import numpy as np
import logging
from typing import List, Dict, Optional
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.services.crud_keyword import keyword as keyword_crud

# 로거 설정
logger = logging.getLogger(__name__)

# 상수 설정
EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_THRESHOLD = 0.4
MAX_SEARCH_LIMIT = 5000

class EmbeddingService:
    def __init__(self):
        # OpenAI 임베딩 모델 초기화
        # 비용 효율적인 text-embedding-3-small 모델 사용
        if settings.OPENAI_API_KEY:
            self.embed_model = OpenAIEmbeddings(
                model=EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY
            )
        else:
            logger.warning("OPENAI_API_KEY not found. Embedding service will be disabled.")
            self.embed_model = None

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a given text.
        """
        if not self.embed_model:
            return []
        
        try:
            return await self.embed_model.aembed_query(text)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def index_keyword(self, keyword_key: str) -> None:
        """
        [Background Task]
        Generates embedding for a keyword and updates the DB.
        Should be called asynchronously.
        """
        if not self.embed_model:
            return

        try:
            # 1. 키워드 데이터 조회
            kw_data = await keyword_crud.get_by_key(keyword_key)
            if not kw_data:
                logger.warning(f"Keyword not found for indexing: {keyword_key}")
                return

            # 2. 임베딩 생성 (키워드 + 정의 결합)
            # 단순 키워드명보다 정의를 포함해야 의미적 검색 품질이 향상됨
            text_to_embed = f"{kw_data.keyword_key}: {kw_data.definition}"
            
            vector = await self.get_embedding(text_to_embed)
            
            if vector:
                # 3. DB 업데이트
                # 주의: CRUDBase.update는 _id(ObjectId 문자열)를 인자로 받음
                await keyword_crud.update(kw_data.id, {"embedding": vector})
                logger.info(f"Indexed keyword: {keyword_key}")
        except Exception as e:
            logger.error(f"Failed to index keyword {keyword_key}: {e}")

    async def search_similar(self, query_text: str, k: int = 3) -> List[Dict]:
        """
        [Sync Task]
        Finds top-k similar keywords from DB using Cosine Similarity.
        TODO: For production (>10k items), migrate to Atlas Vector Search or Pinecone.
        """
        if not self.embed_model:
            return []

        try:
            # 1. 쿼리 텍스트 임베딩 생성
            query_vector = await self.get_embedding(query_text)
            if not query_vector:
                return []
            
            # 2. 비교 대상 전체 키워드 조회 (메모리 로드)
            # 현재 데이터 규모(< 1000개)에서는 전체 로드 후 numpy 연산이 가장 빠름
            # 데이터가 커지면 Vector DB로 마이그레이션 필요
            all_keywords = await keyword_crud.get_multi(limit=MAX_SEARCH_LIMIT) 
            
            cand_vectors = []
            cand_keys = []
            cand_docs = []

            # 임베딩이 존재하는 데이터만 필터링
            for kw in all_keywords:
                if kw.embedding:
                    cand_vectors.append(kw.embedding)
                    cand_keys.append(kw.keyword_key)
                    cand_docs.append(kw)
            
            if not cand_vectors:
                return []

            # 3. 코사인 유사도 계산 (Numpy Vectorization)
            # 유사도 공식: (A . B) / (|A| * |B|)
            # OpenAI 임베딩은 이미 정규화(normalized) 되어 있으므로 내적(Add)만 계산하면 됨
            query_vec_np = np.array(query_vector)
            cand_mat_np = np.array(cand_vectors)
            
            scores = np.dot(cand_mat_np, query_vec_np)
            
            # 4. 상위 K개 추출
            # 점수 기준 내림차순 정렬 후 인덱스 추출
            top_k = min(len(scores), k)
            top_indices = np.argsort(scores)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                score = float(scores[idx])
                
                # 임계값(Threshold) 필터링
                if score > SIMILARITY_THRESHOLD:
                    results.append({
                        "keyword": cand_keys[idx],
                        "score": score,
                        "data": cand_docs[idx].model_dump()
                    })
                    
            return results
        except Exception as e:
            logger.error(f"Error checking similar keywords: {e}")
            return []

    async def calculate_recommendation(self, user_id: str):
        """
        [Background Task]
        Updates user's recommended keywords based on their learning history.
        """
        # 추천 로직 (추후 구현 예정)
        # 1. 사용자가 학습 완료한 키워드 조회
        # 2. 관련성 높은 미학습 키워드 탐색
        # 3. 사용자 프로필 업데이트
        pass

embedding_service = EmbeddingService()

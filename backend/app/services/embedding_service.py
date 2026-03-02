import numpy as np
import logging
from typing import List, Dict, Optional
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from datetime import datetime
from app.services.crud_keyword import keyword as keyword_crud

# 로거 설정
logger = logging.getLogger(__name__)

# 상수 설정
EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_THRESHOLD = 0.85
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

    async def search_by_text(self, query_text: str, k: int = 3, threshold: Optional[float] = None) -> List[Dict]:
        """
        [Sync Task]
        Finds top-k similar keywords from DB using Cosine Similarity by text.
        """
        if not self.embed_model:
            return []

        try:
            # 1. 쿼리 텍스트 임베딩 생성
            query_vector = await self.get_embedding(query_text)
            if not query_vector:
                return []
            
            # 2. 비교 대상 전체 키워드 조회 (메모리 로드)
            all_keywords = await keyword_crud.get_multi(limit=MAX_SEARCH_LIMIT) 
            
            cand_vectors = []
            cand_keys = []
            cand_docs = []

            for kw in all_keywords:
                if kw.embedding:
                    cand_vectors.append(kw.embedding)
                    cand_keys.append(kw.keyword_key)
                    cand_docs.append(kw)
            
            if not cand_vectors:
                return []

            # 3. 코사인 유사도 계산
            query_vec_np = np.array(query_vector)
            cand_mat_np = np.array(cand_vectors)
            
            scores = np.dot(cand_mat_np, query_vec_np)
            
            # 4. 상위 K개 추출
            top_k = min(len(scores), k)
            top_indices = np.argsort(scores)[-top_k:][::-1]
            
            results = []
            # 파라미터로 넘어온 threshold가 있으면 그걸 쓰고 없으면 전역 상수를 사용
            applied_threshold = threshold if threshold is not None else SIMILARITY_THRESHOLD

            for idx in top_indices:
                score = float(scores[idx])
                
                # 임계값(Threshold) 필터링
                if score > applied_threshold:
                    results.append({
                        "keyword": cand_keys[idx],
                        "score": score,
                        "data": cand_docs[idx].model_dump()
                    })
                    
            return results
        except Exception as e:
            logger.error(f"Error checking similar keywords: {e}")
            return []


    async def search_similar(self, user_id: str, k: int = 3) -> List[Dict]:
        """
        사용자의 DB에서 keyword_progress 정보를 바탕으로 지금까지 진행한 키워드를 바탕으로 다음 키워드를 추천합니다.
        평균 벡터를 사용할 경우 주제가 희석되어 유사도가 낮게 나오는 문제를 해결하기 위해,
        Max Similarity 방식 (후보 키워드가 사용자의 어떤 학습 키워드와라도 연관성이 높으면 추천)을 사용합니다.
        """
        if not self.embed_model:
            return []

        try:
            from app.services.crud_user import user as user_crud
            if "@" in user_id:
                user = await user_crud.get_by_email(user_id)
            else:
                user = await user_crud.get(user_id)
                
            if not user:
                return []

            user_kw_keys = set(user.keyword_progress.keys())
            if not user_kw_keys:
                return []

            # 1. 전체 키워드 데이터 메모리 로드
            all_keywords = await keyword_crud.get_multi(limit=MAX_SEARCH_LIMIT)
            
            user_vectors = []
            cand_vectors = []
            cand_keys = []
            cand_docs = []

            for kw in all_keywords:
                if not kw.embedding:
                    continue
                # 사용자가 진행한 적이 있다면 사용자 히스토리에 추가
                if kw.keyword_key in user_kw_keys:
                    user_vectors.append(kw.embedding)
                    
                # 후보 벡터로는 사용자가 아직 한 번도 접하지 않은 새로운 키워드만 추가합니다.
                if kw.keyword_key not in user_kw_keys:
                    cand_vectors.append(kw.embedding)
                    cand_keys.append(kw.keyword_key)
                    cand_docs.append(kw)

            if not user_vectors or not cand_vectors:
                return []

            # 2. 사용자 벡터와 후보 벡터 배열 변환 (Max Similarity 방식 적용)
            history_matrix = np.array(user_vectors)
            cand_mat_np = np.array(cand_vectors)
            
            # 코사인 유사도를 위해 각 벡터 정규화
            hist_norms = np.linalg.norm(history_matrix, axis=1, keepdims=True)
            history_matrix = np.divide(history_matrix, hist_norms, out=np.zeros_like(history_matrix), where=hist_norms!=0)
            
            cand_norms = np.linalg.norm(cand_mat_np, axis=1, keepdims=True)
            cand_mat_np = np.divide(cand_mat_np, cand_norms, out=np.zeros_like(cand_mat_np), where=cand_norms!=0)

            # 3. 코사인 유사도 계산 (후보군 vs 전체 사용자 히스토리)
            # 후보 벡터와 모든 사용자 히스토리 벡터 간의 유사도 행렬 계산
            similarity_matrix = np.dot(cand_mat_np, history_matrix.T)
            
            # 각 후보군에 대해 사용자가 학습한 키워드와의 유사도 중 가장 높은 값을 채택 (희석 방지)
            scores = np.max(similarity_matrix, axis=1)
            
            # 4. 상위 K개 추출
            top_k = min(len(scores), k)
            top_indices = np.argsort(scores)[-top_k:][::-1]
            
            recommendations = []
            for idx in top_indices:
                score = float(scores[idx])
                if score > 0.1: # 연관성이 약간이라도 있는 항목들 포함
                    recommendations.append({
                        "keyword": cand_keys[idx],
                        "score": score,
                        "data": cand_docs[idx].model_dump()
                    })

            return recommendations
            
        except Exception as e:
            logger.error(f"Error in search_similar for user {user_id}: {e}")
            return []

    async def calculate_recommendation(self, user_id: str) -> None:
        """
        Updates user's recommended keywords based on their learning history.
        Uses the enhanced search_similar logic.
        """
        if not self.embed_model:
            return

        try:
            # 1. 사용자 정보 조회
            from app.services.crud_user import user as user_crud
            if "@" in user_id:
                user = await user_crud.get_by_email(user_id)
            else:
                user = await user_crud.get(user_id)
                
            if not user:
                return

            # 2. search_similar를 통해 다음 키워드들 추천받기
            sim_items = await self.search_similar(user_id, k=15)
            
            recommendations_set = []
            if sim_items:
                for item in sim_items:
                    cand_kw = item["keyword"]
                    if cand_kw not in recommendations_set:
                        recommendations_set.append(cand_kw)
            
            # 3. 최대 15개 저장
            new_recommendations = recommendations_set[:15]
            
            if new_recommendations:
                # DB 업데이트
                await user_crud.update(user.id, {"recommended_keywords": new_recommendations})
                logger.info(f"Updated recommendations for user {user_id}: {new_recommendations}")
                
        except Exception as e:
            logger.error(f"Error calculating recommendations for user {user_id}: {e}")
            
embedding_service = EmbeddingService()

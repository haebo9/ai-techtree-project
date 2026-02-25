import streamlit as st
import sys
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from streamlit_agraph import agraph, Node, Edge, Config

# --- Backend Context Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

MONGO_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME", "ai_techtree")

# Streamlit의 쓰레딩 모델 충돌과 Event Loop closed (Motor) 버그를 피해 
# 동기적으로(Sync) MongoDB 쿼리를 수행하도록 MongoClient를 직접 활용합니다.
@st.cache_resource
def get_db():
    if not MONGO_URL:
        st.error("MONGODB_URL 환경 변수가 없습니다.")
        return None
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]

db = get_db()
if db is not None:
    users_col = db["users"]
    keywords_col = db["keywords"]

# --- Streamlit UI Configurations ---
st.set_page_config(page_title="AI TechTree - Keyword Node Visualizer", page_icon="🧬", layout="wide")

st.title("🧬 User Keyword Knowledge Graph")
st.markdown("사용자가 즐긴 키워드들의 임베딩 벡터 값과 **streamlit-agraph** 라이브러리를 통해, 코사인 유사도가 높은 키워드끼리 인력이 발생하도록 **동적인 관계망**을 시각화합니다.")

st.sidebar.header("⚙️ Settings")
user_email = st.sidebar.text_input("User ID (Email)", value="test_user@ai-techtree.com")
similarity_threshold = st.sidebar.slider("Similarity Threshold (Edges)", min_value=0.10, max_value=0.99, value=0.50, step=0.01)

# --- Database & Embedding Retrieval Logic ---
def load_user_graph_data(email: str):
    if db is None:
        return None, "DB 연결이 되어있지 않습니다."
        
    user_data = users_col.find_one({"auth.email": email})
    # 이메일로 못 찾으면 일반 ID 문서로도 하위조회 (fallback)
    if not user_data:
        user_data = users_col.find_one({"_id": email}) 
    
    if not user_data:
        return None, "존재하지 않는 사용자입니다."
    
    progress = user_data.get("keyword_progress", {})
    if not progress:
        return None, "사용자가 아직 학습을 진행한 키워드가 없습니다."
    
    learned_keys = list(progress.keys())
    keywords_data = []
    
    for kw_key in learned_keys:
        kw = keywords_col.find_one({"keyword_key": kw_key})
        if kw and "embedding" in kw and len(kw["embedding"]) > 0:
            star_rating = progress[kw_key].get("star", 0)
            keywords_data.append({
                "keyword": kw_key,
                "star": star_rating,
                "embedding": kw["embedding"]
            })
            
    if not keywords_data:
        return None, "키워드는 있지만 임베딩 벡터가 생성된 키워드가 하나도 없습니다."
        
    return keywords_data, None

# --- Graph Generation Logic (streamlit-agraph) ---
def draw_agraph(keywords_data, threshold):
    labels = [d["keyword"] for d in keywords_data]
    embeddings = np.array([d["embedding"] for d in keywords_data])
    stars = [d["star"] for d in keywords_data]
    
    # Cosine Similarity 행렬 계산
    sim_matrix = cosine_similarity(embeddings)
    
    # 노드 색상 지정 (별 개수 기반)
    color_map = {0: '#E0E0E0', 1: '#CD7F32', 2: '#C0C0C0', 3: '#FFD700'}
    
    nodes = []
    edges = []
    
    for i, label in enumerate(labels):
        star = stars[i]
        star_str = "⭐" * star + "☆" * (3 - star) if star > 0 else "학습 전"
        
        # 1. 아그래프(agraph) 노드(Node) 추가
        nodes.append(Node(
            id=label,
            label=label,
            size=15 + star * 5,
            color=color_map.get(star, '#888'),
            title=f"키워드: {label} \\n레벨: {star_str}" # Hover 시 보여지는 툴팁
        ))
        
    num_nodes = len(labels)
    max_sim = 0.0
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            sim = sim_matrix[i, j]
            if sim > max_sim:
                max_sim = float(sim)
            if sim >= threshold:
                edges.append(Edge(
                    source=labels[i],
                    target=labels[j],
                    title=f"코사인 유사도: {sim:.3f}", 
                    color="#A0A0A0",
                    value=float(sim * 5),
                    width=2
                ))
    
    # 3. 레이아웃과 물리엔진 설정 (Config)
    config = Config(
        width=1000, 
        height=600,
        directed=False, 
        physics=True, # 노드 간의 인력/척력을 물리 시뮬레이션으로 자동 계산 
        hierarchical=False,
    )
    
    return nodes, edges, config, max_sim

# --- App Execution ---
if st.button("🚀 임베딩 시각화 실행 (Generate Graph)"):
    with st.spinner("DB에서 데이터를 불러오고 화면을 렌더링 중입니다..."):
        keywords_data, error = load_user_graph_data(user_email)
            
        if error:
            st.warning(error)
        else:
            nodes, edges, config, max_sim = draw_agraph(keywords_data, similarity_threshold)
            st.success(f"데이터 로드 완료! 총 {len(nodes)}개의 키워드 노드와 {len(edges)}개의 선(Edge)을 생성했습니다.")
            st.info(f"💡 현재 획득한 키워드간 최고 유사도: {max_sim:.3f}")
            
            # Interactive 렌더링
            return_value = agraph(nodes=nodes, edges=edges, config=config)
            
            # Raw 데이터 보여주기 (토글)
            with st.expander("📊 획득한 키워드 원본 데이터 확인 (Raw Data)"):
                st.dataframe([
                    {"Keyword": k["keyword"], "Star Rating": k["star"], "Vector Dim": len(k["embedding"])} 
                    for k in keywords_data
                ])

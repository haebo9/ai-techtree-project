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
import os
from PIL import Image

logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app/source/techtree-tree.png")
page_icon_img = Image.open(logo_path) if os.path.exists(logo_path) else "🧬"

st.set_page_config(page_title="TechTree", page_icon=page_icon_img, layout="wide")

st.markdown("""
    <style>
        /* 깔끔하고 연한 푸른빛 회색 (아이보리) 배경 적용 */
        .stApp {
            background-color: #F4F6F9 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #F4F6F9 !important;
        }
        
        /* 채팅/그래프 컨테이너 테두리 명확하게 지정 */
        div[data-testid="stContainer"] {
            border-color: #555555 !important;
        }
        
        /* 상단 여백 보정 (너무 바짝 붙지 않도록) */
        .block-container {
            padding-top: 4rem !important;
        }
    </style>
""", unsafe_allow_html=True)
# 상단 헤더 로고 및 타이틀 배치
import os
import base64

logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app/source/techtree-tree.png")
logo_html = ""

if os.path.exists(logo_path):
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    # 로고 이미지를 텍스트 크기에 맞춰 작고 예쁘게 조정
    logo_html = f'<img src="data:image/png;base64,{encoded_string}" style="height: 50px; margin-right: 15px; vertical-align: middle; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'

st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
        {logo_html}
        <h1 style="margin: 0; padding: 0;">AI TechTree (Beta)</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown('나만의 기술 트리 맵을 완성해보세요! &nbsp;|&nbsp; **Developer:** <a href="https://github.com/haebo9" target="_blank" style="text-decoration: none; font-weight: bold;">@haebo9</a>', unsafe_allow_html=True)

import uuid

# --- Session & Guest User Initialization ---
if "user_id" not in st.session_state:
    st.session_state.user_id = f"guest_{uuid.uuid4().hex[:8]}"
    # 시작 시 빈 화면을 방지하고 최소한의 시작 지점을 제공합니다.
    if db is not None:
        try:
            users_col.insert_one({
                "_id": st.session_state.user_id,
                "auth": {"email": st.session_state.user_id},
                "keyword_progress": {
                    "Python": {"star": 0, "quiz_history": []}
                }
            })
        except Exception:
            pass

st.sidebar.header("⚙️ Settings")
user_email = st.sidebar.text_input("User ID (Guest)", value=st.session_state.user_id, disabled=True)
similarity_threshold = st.sidebar.slider("Similarity Threshold (Edges)", min_value=0.10, max_value=0.99, value=0.37, step=0.01)

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
        return None, "첫 번째 퀴즈를 진행하여 나만의 기술 트리를 생성해 보세요! (좌측 하단 입력창 사용)"
    
    learned_keys = list(progress.keys())
    keywords_data = []
    
    for kw_key in learned_keys:
        kw = keywords_col.find_one({"keyword_key": kw_key})
        if kw and "embedding" in kw and len(kw["embedding"]) > 0:
            star_rating = progress[kw_key].get("star", 0)
            keywords_data.append({
                "keyword": kw_key,
                "star": star_rating,
                "embedding": kw["embedding"],
                "definition": kw.get("definition", ""),
                "summary": kw.get("summary", "")
            })
            
    if not keywords_data:
        return None, "첫 번째 퀴즈를 진행하여 나만의 기술 트리를 생성해 보세요! (좌측 하단 입력창 사용)"
        
    return keywords_data, None

# --- Graph Generation Logic (streamlit-agraph) ---
def draw_agraph(keywords_data, threshold):
    labels = [d["keyword"] for d in keywords_data]
    embeddings = np.array([d["embedding"] for d in keywords_data])
    stars = [d["star"] for d in keywords_data]
    
    # Cosine Similarity 행렬 계산
    sim_matrix = cosine_similarity(embeddings)
    
    # 노드 색상 지정 (별 개수 기반: 0:옅은 회색, 1:짙은 노란색, 2:주황색, 3:빨간색)
    color_map = {0: '#E0E0E0', 1: '#FFB300', 2: '#FF7F00', 3: '#FF3333'}
    
    nodes = []
    edges = []
    
    for i, label in enumerate(labels):
        star = stars[i]
        star_str = "⭐" * star + "☆" * (3 - star) if star > 0 else "None"
        
        # 1. 아그래프(agraph) 노드(Node) 추가
        nodes.append(Node(
            id=label,
            label=label,
            size=15 + star * 5,
            color=color_map.get(star, '#888'),
            title=f"키워드: {label}\n레벨: {star_str}" # Hover 시 보여지는 툴팁
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
    
    config = Config(
        width='100%', 
        height=600,
        directed=False, 
        physics=True, # 노드 간의 인력/척력을 물리 시뮬레이션으로 자동 계산 
        hierarchical=False,
    )
    
    return nodes, edges, config, max_sim

import httpx

# --- App Execution & Layout ---
col1, col2 = st.columns([3, 4])

def init_chat_session():
    st.session_state.messages = []
    try:
        # 랭그래프 서버(2024 포트)에 명시적인 JSON Payload와 함께 스레드를 정상 생성합니다.
        resp = httpx.post("http://127.0.0.1:2024/threads", json={}, timeout=5.0)
        resp.raise_for_status() 
        st.session_state.thread_id = resp.json().get("thread_id")
    except Exception as e:
        st.error(f"채팅 서버 초기화 실패: {e}")
        st.session_state.thread_id = None

# Session State for Chat
if "messages" not in st.session_state or "thread_id" not in st.session_state or st.session_state.thread_id is None:
    init_chat_session()

with col1:
    c_title, c_btn = st.columns([9, 1])
    with c_title:
        st.subheader("Developer Quiz")
    with c_btn:
        if st.button("🔄", help="채팅 초기화"):
            init_chat_session()
            st.rerun()
            
    st.markdown("학습을 원하는 개념 키워드를 입력해주세요. \n새로운 키워드 진행 시 오른쪽 그래프가 업데이트 됩니다.")
    
    # Render chat history in a fixed-height scrollable container
    chat_container = st.container(height=700, border=False)
    with chat_container:
        if len(st.session_state.messages) == 0:
            st.markdown(
                """<div style='text-align: center; color: #444; padding: 30px 10px; font-size: 0.95em; line-height: 1.6;'>
                <h3 style='color: #2c3e50; margin-bottom: 10px; font-weight: 700;'>🌱 AI TechTree에 오신 것을 환영합니다!</h3>
                <p style='margin-bottom: 25px; font-size: 1.05em; color: #555;'>
                채팅창에 배우고 싶은 <b>IT 개념이나 기술 키워드</b>를 입력해 보세요.<br>
                수준별 퀴즈를 통해 학습하고, 나만의 기술 지도를 완성 할수 있습니다.
                </p>
                <div style='text-align: left; display: inline-block; background-color: #ffffff; padding: 25px 30px; border-radius: 12px; border: 1px solid #e0e0e0; box-shadow: 0 4px 6px rgba(0,0,0,0.02); max-width: 650px;'>
                <div style='border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 15px;'>
                <b style='font-size: 1.1em; color:#333;'>🚀 핵심 기능 가이드</b>
                </div>
                <ul style='list-style-type: none; padding-left: 0; margin-bottom: 20px;'>
                <li style='margin-bottom: 12px;'>💬 <b>개념 학습 & 맞춤 퀴즈:</b> 특정 기술을 입력하면 맞춤형 설명과 퀴즈가 진행됩니다.</li>
                <li style='margin-bottom: 12px;'>⭐ <b>답변 기반 레벨업:</b> 퀴즈 정답 결과에 따라 별점을 획득하고 기술 레벨(Lv.1~3)이 오릅니다.</li>
                <li style='margin-bottom: 12px;'>📈 <b>실시간 기술 맵 연동:</b> 획득한 키워드들의 유사도를 바탕으로 기술 맵이 그려집니다.</li>
                </ul>
                <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; font-size: 0.9em; color: #555;'>
                <b style='color:#444; display:block; margin-bottom:8px;'>🎯 레벨별 노드 색상표</b>
                <div style='display: flex; gap: 10px; flex-wrap: wrap; text-align: center; font-size: 0.95em;'>
                <span style='background: #E0E0E0; padding: 4px 8px; border-radius: 6px; color: #333;'>⚪ Lv.0 (학습 전)</span>
                <span style='background: #FFB300; padding: 4px 8px; border-radius: 6px; color: #fff; font-weight: 500;'>🟡 Lv.1 (기 초)</span>
                <span style='background: #FF7F00; padding: 4px 8px; border-radius: 6px; color: #fff; font-weight: 500;'>🟠 Lv.2 (심 화)</span>
                <span style='background: #FF3333; padding: 4px 8px; border-radius: 6px; color: #fff; font-weight: 500;'>🔴 Lv.3 (마스터)</span>
                </div>
                </div>
                </div>
                <div style='margin-top: 25px; color: #7f8c8d; font-size: 0.95em;'>
                <i>💡 <b>Tip</b> : 하단 입력창을 클릭해 대화를 시작해 보세요!</i>
                </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
        else:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
    # Input box
    prompt = st.chat_input("ex. 파이썬 공부할래. 다음 키워드 추천해줘")
    
    # Programmatic trigger support via session state
    if st.session_state.get("submit_prompt"):
        prompt = st.session_state.submit_prompt
        st.session_state.submit_prompt = None

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 새 메시지가 입력되었을 때 컨테이너 안에 즉시 렌더링
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
                
            with st.chat_message("assistant"):
                answer_placeholder = st.empty()
                with st.spinner("처리중..."):
                    try:
                        # LangGraph Dev 서버의 2024 포트로 Streaming 요청을 보냅니다.
                        API_URL = "http://127.0.0.1:2024/threads/{}/runs/stream"
                        
                        payload = {
                            "assistant_id": "agent",
                            "input": {
                                "messages": [{"role": "user", "content": prompt}],
                                "user_id": user_email,
                                "user_intent": "General", 
                                "topic": "General" 
                            },
                            "stream_mode": "values"
                        }
                        
                        full_response = ""
                        with httpx.stream("POST", API_URL.format(st.session_state.thread_id), json=payload, timeout=60.0) as r:
                             if r.status_code == 200:
                                 for line in r.iter_lines():
                                     if line and line.startswith("data: "):
                                         import json
                                         try:
                                             data = json.loads(line[6:])
                                             if "messages" in data and len(data["messages"]) > 0:
                                                 msgs = data["messages"]
                                                 
                                                 # 마지막 Human 메시지 이후의 모든 AI 메시지 찾기
                                                 last_human_idx = -1
                                                 for i in range(len(msgs) - 1, -1, -1):
                                                     if msgs[i].get("type") == "human":
                                                         last_human_idx = i
                                                         break
                                                 
                                                 if last_human_idx != -1:
                                                     new_ai_msgs = msgs[last_human_idx+1:]
                                                     if new_ai_msgs:
                                                         contents = [m["content"] for m in new_ai_msgs if m.get("type") == "ai" and m.get("content")]
                                                         if contents:
                                                             full_response = "\n\n".join(contents)
                                                             answer_placeholder.markdown(full_response + " ▌")
                                         except:
                                             pass
                                 answer_placeholder.markdown(full_response)
                             else:
                                 error_text = r.read().decode('utf-8', errors='ignore')
                                 full_response = f"API Error ({r.status_code}): {error_text}"
                                 answer_placeholder.error(full_response)
                                 
                    except Exception as e:
                        full_response = f"LangGraph 연결 실패: 서버를 켜주세요. (`langgraph dev`) \\n({e})"
                        answer_placeholder.error(full_response)
                            
                st.session_state.messages.append({"role": "assistant", "content": full_response})

with col2:
    c_title2, c_btn2 = st.columns([9, 1])
    with c_title2:
        st.subheader("Keyword Map")
    with c_btn2:
        if st.button("🔄", help="그래프 새로고침"):
            st.rerun()
            
    with st.spinner("DB에서 데이터를 불러오고 화면을 렌더링 중입니다..."):
        keywords_data, error = load_user_graph_data(user_email)
            
        if error:
            st.warning(error)
        else:
            nodes, edges, config, max_sim = draw_agraph(keywords_data, similarity_threshold)
            st.success(f"총 {len(nodes)}개의 키워드와 {len(edges)}개의 관계를 생성했습니다. (tip. 노드를 움직여보세요)")
            # st.info(f"💡 현재 획득한 키워드간 최고 유사도: {max_sim:.3f}")
            
            # Interactive 렌더링 (테두리 모서리 박스 추가)
            st.markdown(
                """
                <style>
                /* Streamlit 의 st.container 테두리 두께 및 색상 조절 */
                div[data-testid="stContainer"] {
                    border: 2px solid #555555 !important; /* 약간 진하고 두꺼운 회색 모서리 */
                    border-radius: 10px !important;
                    padding: 0px !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            with st.container(border=True):
                return_value = agraph(nodes=nodes, edges=edges, config=config)
            
            # 노드 클릭 시 반환된 id(키워드) 처리
            if return_value:
                selected_kw = next((item for item in keywords_data if item["keyword"] == return_value), None)
                if selected_kw:
                    star = selected_kw['star']
                    star_str = "⭐" * star + "☆" * (3 - star) if star > 0 else "☆"*3
                    definition = selected_kw.get('definition', "DB에 상세 정의가 존재하지 않습니다.")
                    summary = selected_kw.get('summary', "")
                    
                    # summary_html = f"<p style='margin-bottom: 12px; font-size: 0.9em; color: #777;'>💡 <b>요약:</b> {summary}</p>" if summary else ""

                    st.markdown(f"""
                        <div style='padding: 15px; background-color: #ffffff; border-radius: 8px; border-left: 4px solid #4CAF50; margin-top: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                            <div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;'>
                                <h4 style='margin: 0; color: #333;'>❗ 선택된 키워드: <b>{selected_kw['keyword']}</b></h4>
                                <span style='font-size: 1.05em; color: #FFB300;'><b>{star_str}</b></span>
                            </div>
                            <div style='background-color: #f9f9f9; padding: 12px; border-radius: 6px; font-size: 0.95em; color: #444; line-height: 1.5;'>
                                <b>📖 개념 정의</b><br>
                                {definition}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"💬 **'{selected_kw['keyword']}' 퀴즈 시작** (⚠️ 진행 중인 퀴즈가 종료됩니다)", key=f"chat_btn_{selected_kw['keyword']}"):
                        init_chat_session()
                        st.session_state.submit_prompt = f"{selected_kw['keyword']}에 대한 퀴즈 진행해줘."
                        st.rerun()

            # # Raw 데이터 보여주기 (토글)
            # with st.expander("📊 획득한 키워드 원본 데이터 확인 (Raw Data)"):
            #     st.dataframe([
            #         {"Keyword": k["keyword"], "Star Rating": k["star"], "Vector Dim": len(k["embedding"])} 
            #         for k in keywords_data
            #     ])

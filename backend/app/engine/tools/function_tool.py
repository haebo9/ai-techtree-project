import os
import json
import threading
import numpy as np
from datetime import datetime
from urllib.parse import urlparse
from langchain_openai import OpenAIEmbeddings
from tavily import TavilyClient

# Database Connection
from app.core.database import get_db

# =========================================================
# 1. Global Setup & Utilities
# =========================================================

# Global instances (Lazy Loaded)
EMBEDDING_MODEL = None
TAVILY_CLIENT = None
TRACK_EMBEDDINGS = {} 

def _get_embedding_model():
    """Lazily initialize Embedding Model (Only for Track Search)."""
    global EMBEDDING_MODEL
    if EMBEDDING_MODEL is None:
        try:
             api_key = os.environ.get("OPENAI_API_KEY")
             if not api_key:
                 raise ValueError("OpenAI API Key not found.")
             EMBEDDING_MODEL = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
        except Exception as e:
            print(f"Failed to initialize embedding model: {e}")
            return None
    return EMBEDDING_MODEL

def _get_tavily_client():
    """Lazily initialize Tavily Client."""
    global TAVILY_CLIENT
    if TAVILY_CLIENT is None:
        try:
            api_key = os.environ.get("TAVILY_API_KEY")
            if api_key:
                TAVILY_CLIENT = TavilyClient(api_key=api_key)
            else:
                print("Warning: TAVILY_API_KEY not found.")
        except Exception as e:
            print(f"Failed to initialize Tavily client: {e}")
    return TAVILY_CLIENT

def _load_track_data() -> dict:
    """
    Loads track data from MongoDB and converts it to the legacy dictionary format.
    Target Collection: tracks
    """
    try:
        db = get_db()
        # Sort by 'order' to maintain Track 0, 1, 2... sequence
        cursor = db["tracks"].find({}).sort("order", 1)
        
        tracks_dict = {}
        for doc in cursor:
            # Use 'title' as the track key (e.g., "Track 0: The Origin")
            track_name = doc.get("title") 
            if not track_name: 
                continue

            # Reconstruct 'steps' dictionary from List[TrackStep]
            steps_dict = {}
            for step in doc.get("steps", []):
                step_name = step.get("step_name")
                step_desc = step.get("description", "")
                
                # Reconstruct 'options' dictionary from List[TrackBranchOption]
                options_dict = {}
                for option in step.get("options", []):
                    option_name = option.get("option_name")
                    option_desc = option.get("description", "")
                    
                    # Reconstruct 'subjects' dictionary from List[TrackSubject]
                    subjects_dict = {}
                    for subject in option.get("subjects", []):
                        subject_title = subject.get("title")
                        subject_desc = subject.get("description", "")
                        
                        # levels is a nested dict or object (LevelsContent)
                        levels = subject.get("levels", {})
                        
                        # If description exists, add it to the subject dict as well (custom format for tool logic)
                        # NOTE: The original logic expects levels dict here. 
                        # To keep it compatible but carry description, we might need a wrapper or just rely on 'description' key if it's treated as a dict.
                        # Ideally, tracks_json structure is: "SubjectName": { "description": "...", "Lv1": [...] }
                        
                        formatted_subject_data = {
                            "Lv1": levels.get("Lv1", []),
                            "Lv2": levels.get("Lv2", []),
                            "Lv3": levels.get("Lv3", [])
                        }
                        if subject_desc:
                            formatted_subject_data["description"] = subject_desc
                            
                        subjects_dict[subject_title] = formatted_subject_data
                    
                    # Same for Option, it needs to be a dict of Subjects but also carry its own description
                    # tracks.json structure: "OptionName": { "description": "...", "Subject1": ... }
                    options_dict[option_name] = subjects_dict
                    if option_desc:
                        options_dict[option_name]["description"] = option_desc
                
                # Same for Step
                steps_dict[step_name] = options_dict
                if step_desc:
                    steps_dict[step_name]["description"] = step_desc
            
            tracks_dict[track_name] = {
                "description": doc.get("description", ""),
                "steps": steps_dict
            }
            
        return tracks_dict

    except Exception as e:
        print(f"Error loading track data from MongoDB: {e}")
        return {} 

def _extract_domain(url: str) -> str:
    """Extracts simplified domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except:
        return ""

def _clean_text(text: str) -> str:
    """Basic text cleaning."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\t", " ").replace("\r", " ")
    return " ".join(text.split())

def _cosine_similarity(vec_a, vec_b):
    """Calculates Cosine Similarity between two vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(vec_a, vec_b) / (norm_a * norm_b)


# =========================================================
# 2. Tool Logic: Survey (get_techtree_survey)
# =========================================================

def f_get_techtree_survey() -> dict:
    """
    Returns the initial survey questions to diagnose user interests and experience.
    Loads data from 'backend/app/source/surveys.json'.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        source_path = os.path.join(current_dir, "..", "source", "surveys.json")
        
        if not os.path.exists(source_path):
             return {"error": f"Survey file not found at {source_path}"}
             
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
            
    except Exception as e:
        print(f"Error loading survey data: {e}")
        return {
            "intro_message": "설문 데이터를 불러오는 중 오류가 발생했습니다.",
            "questions": []
        }


# =========================================================
# 3. Tool Logic: Track Recommendation (get_techtree_track)
# =========================================================

def _initialize_track_embeddings():
    """Lazily initializes embeddings for all tracks."""
    if TRACK_EMBEDDINGS:
        return
    
    model = _get_embedding_model()
    if not model:
        return

    texts = []
    keys = []
    ai_tech_tree = _load_track_data()
    for track_name, track_data in ai_tech_tree.items():
        description = track_data.get("description", "")
        # Include Step names to enhance context
        steps_content = []
        if "steps" in track_data:
            for step_name in track_data["steps"].keys():
                steps_content.append(step_name)
        
        full_text = f"{track_name}. {description}. Key Areas: {', '.join(steps_content)}"
        texts.append(full_text)
        keys.append(track_name)
    
    try:
        embeddings = model.embed_documents(texts)
        for key, vector in zip(keys, embeddings):
            TRACK_EMBEDDINGS[key] = vector
    except Exception as e:
        print(f"Error generating embeddings: {e}")

def perform_search_similarity(query_text: str) -> dict:
    """Finds best matching track using embedding similarity."""
    _initialize_track_embeddings()
    if not TRACK_EMBEDDINGS:
         return {"error": "Failed to initialize embeddings."}
         
    model = _get_embedding_model()
    if not model:
        return {"error": "Embedding model not initialized."}

    try:
        query_vector = model.embed_query(query_text)
    except Exception as e:
        return {"error": f"Embedding generation failed: {e}"}
    
    best_track = None
    best_score = -1.0
    
    for track_name, track_vector in TRACK_EMBEDDINGS.items():
        score = _cosine_similarity(query_vector, track_vector)
        if score > best_score:
            best_score = score
            best_track = track_name
            
    return {"best_track": best_track, "score": best_score}

def f_get_techtree_track(interests: list[str], experience_level: str) -> dict:
    """
    Main logic for 'get_ai_track'.
    Handles both 'list all' requests and semantic search recommendations.
    """
    # 0. Check for "List All" request
    check_keywords = {k.upper() for k in interests}
    if any(k in check_keywords for k in ["ALL", "LIST", "TRACKS", "전체", "목록"]) or not interests:
        all_tracks = []
        ai_tech_tree = _load_track_data()
        for name, data in ai_tech_tree.items():
            all_tracks.append({
                "track_name": name,
                "description": data.get("description", "")
            })
        return {"available_tracks": all_tracks, "message": "Here are all the available AI Tech Tracks."}

    # 1. Semantic Search
    query_text = " ".join(interests)
    result = perform_search_similarity(query_text)
    
    if "error" in result:
        return result
        
    best_track = result.get("best_track")
    best_score = result.get("score")

    # 2. Construct detailed result
    if best_track:
        ai_tech_tree = _load_track_data()
        track_info = ai_tech_tree[best_track]
        
        # Construct a rich summary of the track content
        track_summary = {
            "track_name": best_track,
            "description": track_info.get("description", ""),
            "key_steps": []
        }
        
        # Add summary of steps to give context to the LLM
        if "steps" in track_info:
            for step_key, step_val in track_info["steps"].items():
                step_summary = {
                    "step": step_key,
                    "description": step_val.get("description", ""), # Add Step description
                    "topics": [k for k in step_val.keys() if k != "description"][:3] # Exclude 'description' key from topics list
                }
                track_summary["key_steps"].append(step_summary)

        return {
            "recommended_track": best_track,
            "description": track_info.get("description", ""),
            "matching_score": round(float(best_score), 2),
            "reason": f"Your interests in '{', '.join(interests)}' match this track's focus on {track_info.get('description', '')}.",
            "track_content": track_summary # Replaced starting_point with rich content
        }
    else:
        return {"error": "No suitable track found."}


# =========================================================
# 4. Tool Logic: Roadmap Details (get_techtree_path)
# =========================================================

def f_get_techtree_path(track_name: str) -> dict:
    """
    Main logic for 'get_ai_path'.
    Retrieves and structures the full roadmap for a specific track.
    """
    ai_tech_tree = _load_track_data()
    track_data = ai_tech_tree.get(track_name)
    
    if not track_data:
        # 1. Fuzzy Search for Candidates
        all_tracks = list(ai_tech_tree.keys())
        matches = [t for t in all_tracks if track_name.lower() in t.lower() or t.lower() in track_name.lower()]
        
        if matches:
             return {
                "error": f"Track '{track_name}' not found exact match.",
                "candidates": matches,
                "guide": f"Did you mean '{matches[0]}'? Retry with the exact track name from the candidates."
            }
        
        # 2. No Match -> Guide to Track Tool
        return {
            "error": f"Track '{track_name}' not found.",
            "guide": "The track name seems incorrect or does not exist. Please Call 'get_techtree_track' with interests=['ALL'] or specific keywords to find the correct track name first."
        }
    
    # Reconstruct hierarchy for better LLM Understanding
    roadmap_structure = {}
    steps = track_data.get("steps", {})
    
    for step_name, step_content in steps.items():
        # step_content has keys: "description", "Option 1...", "Option 2..."
        # We need to preserve step description? The output schema Dict[str, List[PathNode]] uses Step Name as Key.
        # Ideally, we put description in the key or pass it separately. 
        # But PathOutput schema has 'roadmap' as Dict[str, List]. 
        # Combining Step Name + Desc in the key is a hack but works for LLM context.
        
        step_desc = step_content.get("description", "")
        # display_step_name = f"{step_name} ({step_desc})" if step_desc else step_name
        # Keep key clean for now, maybe add a special node? or just rely on Subject descriptions.
        # Let's keep key clean. The LLM can infer from Subject descriptions. 
        # OR: we could append a 'Summary Node' at the start of the list.
        
        roadmap_structure[step_name] = []
        
        for key, val in step_content.items():
            if key == "description": continue

            # Check if it's a direct Subject (Level 1)
            # val is a dict. If it has "Lv1", it's a Subject (or Option pretending to be Subject)
            if isinstance(val, dict) and "Lv1" in val:
                subject_info = {
                    "subject": key,
                    "description": val.get("description", ""), 
                    "importance": "High"
                }
                roadmap_structure[step_name].append(subject_info)
            else: 
                # It's a Group/Option (Nested)
                # val is { "description": "...", "Subject1": ... }
                option_desc = val.get("description", "")
                
                for sub_key, sub_val in val.items():
                     if sub_key == "description": continue
                     
                     if isinstance(sub_val, dict) and "Lv1" in sub_val:
                         # Merge Option desc with Subject desc for better context?
                         # Or just pass Subject desc.
                         subj_desc = sub_val.get("description", "")
                         
                         full_desc = subj_desc
                         if option_desc and not subj_desc:
                             full_desc = f"[{key}] {option_desc}" # Fallback to Option desc if specific subj desc missing?
                         elif option_desc and subj_desc:
                             full_desc = f"({key}) {subj_desc}"

                         subject_info = {
                            "subject": sub_key,
                            "category": key, # e.g. "Language"
                            "description": full_desc,
                            "importance": "Medium"
                        }
                         roadmap_structure[step_name].append(subject_info)
    
    return {
        "track": track_name,
        "description": track_data.get("description"),
        "roadmap": roadmap_structure,
        "note": "Use 'get_techtree_detail' for specific subject details."
    }


# =========================================================
# 5. Tool Logic: Subject Details (get_techtree_subject)
# =========================================================

def f_get_techtree_subject(subject_name: str) -> dict:
    """
    Finds detailed concepts (Lv1, Lv2, Lv3) for a specific subject across all tracks.
    Used by 'get_techtree_detail'.
    """
    # Normalize query
    query = subject_name.lower().strip()
    
    ai_tech_tree = _load_track_data()
    # =========================================================
    # Refined Logic: Exact -> Fuzzy -> Guidance
    # =========================================================
    
    # 1. Collect all subjects first for search
    matches = []
    
    ai_tech_tree = _load_track_data()
    for track_name, track_val in ai_tech_tree.items():
        for step_name, step_val in track_val.get("steps", {}).items():
            for key, val in step_val.items():
                if isinstance(val, dict):
                    # Check Level 1 (Subject)
                    if key.lower() == query:
                         return {"subject": key, "track": track_name, "details": val}
                    if query in key.lower():
                        matches.append(key)
                        
                    # Check Group/Option Nested
                    if "Lv1" not in val:
                         for sub_key, sub_val in val.items():
                            if isinstance(sub_val, dict):
                                if sub_key.lower() == query:
                                    return {"subject": sub_key, "track": track_name, "category": key, "details": sub_val}
                                if query in sub_key.lower():
                                    matches.append(sub_key)

    # 2. Fuzzy Match Results (Partially Found)
    if matches:
        # Remove duplicates and sort
        unique_matches = sorted(list(set(matches)))
        return {
            "error": f"Subject '{subject_name}' not found exact match.",
            "message": f"Did you mean one of these? {', '.join(unique_matches[:5])}",
            "candidates": unique_matches[:5]
        }

    # 3. Not Found -> Guide Agent to use Track Tool
    return {
        "error": f"Subject '{subject_name}' not found in the curriculum.",
        "guide": f"RECOMMENDATION: The concept '{subject_name}' might be part of a broader track. Please Call 'get_techtree_track' with interests=['{subject_name}'] to find the relevant track first."
    }


# =========================================================
# 6. Tool Logic: Trends (get_techtree_trend)
# =========================================================

def _process_and_save_background(results: list[dict], search_terms: list[str], category: str = "tech_news"):
    """
    Background Task: Clean content and save unique items to MongoDB 'trends' collection (Grouped by Category).
    """
    try:
        db = get_db()
        collection = db["trends"]
        
        for res in results:
            link = res.get("url")
            if not link: 
                continue

            # Check for duplicates using the link WITHIN the specific category
            # We look for a document with this category that ALREADY has this link in 'items'
            exists = collection.find_one({
                "category": category,
                "items.link": link
            })
            
            if exists:
                continue
            
            clean_summary = _clean_text(res.get("content", ""))[:800] + "..."
            domain = _extract_domain(link)
            
            new_item = {
                "title": _clean_text(res.get("title")),
                "link": link,
                "summary": clean_summary,
                "tags": search_terms,
                "source_domain": domain,
                "collected_at": datetime.utcnow(),
                "view_count": 0
            }
            
            # Upsert logic: Update the array of the category document
            collection.update_one(
                {"category": category},
                {
                    "$push": {"items": new_item},
                    "$set": {"last_updated": datetime.utcnow()}
                },
                upsert=True
            )
            print(f"[Async] Saved new trend to category '{category}': {new_item['title']}")
            
    except Exception as e:
        print(f"[Async] Background save to MongoDB failed: {e}")

def f_get_techtree_trend(keywords: list[str], category: str = "tech_news") -> list[dict]:
    """
    Executes web search using Tavily with domain filtering and background archiving.
    """
    client = _get_tavily_client()
    if not client:
        return {
            "answer": "검색 클라이언트를 사용할 수 없습니다.",
            "items": [{"title": "System Error", "link": "", "summary": "Search client not available."}]
        }

    # 1. 키워드 정규화 및 쿼리 생성
    search_terms = [k.lower().strip() for k in keywords if k.strip()]
    query_text = " ".join(keywords)
    
    # 현재 연도(2026년)를 반영한 최신 트렌드 쿼리 최적화
    if category == "k_blog":
         search_query = query_text
    else:
         search_query = f"Latest technical trends, insights, and news about {query_text} in 2025-2026"
    
    # 2. Domain Filtering Configuration
    DOMAIN_MAP = {
        "tech_news": [  
            "news.hada.io",                 # GeekNews (High Quality Curated)
        ],
        "engineering": [
            "github.com",                   # Open Source
            "huggingface.co",               # AI Models & Papers
            "openai.com",                   # Official Blog
            "anthropic.com",                # Official Blog
            "langchain.com/blog",           # AI 앱 개발 메타
            "wandb.ai/fully-connected",     # 실무 엔지니어링
            "pytorch.org/blog",             # Official Framework Blog
        ],
        "research": [   
            "arxiv.org",                    # Research Papers
            "paperswithcode.com",           # Papers + Code
            "deepmind.google/research",     # DeepMind Research
            "research.google",              # Google Research
            "scholar.google.com",           # Google Scholar
            "openreview.net"                # Academic Reviews
        ],
        "k_blog": [      
            "techblog.woowahan.com",        # Woowa Bros
            "medium.com/daangn",            # Daangn Market
            "toss.tech",                    # Toss
            "devocean.sk.com",              # SK
            "helloworld.kurly.com",         # Kurly
            "techblog.lycorp.co.jp/ko",     # LINE
            "d2.naver.com",                 # Naver D2
            "kakaoenterprise.com",          # Kakao Enterprise
            "hyperconnect.com",             # Hyperconnect
            "ridicorp.com/story",           # Ridi
            "netmarble.engineering",        # Netmarble
        ]
    }
    
    target_domains = DOMAIN_MAP.get(category.lower(), DOMAIN_MAP["k_blog"])
    tavily_answer = "advanced" # Advanced(LLM) or Basic(Simple)
    tavily_topic = "general" # "general", "news" and "finance

    try:
        # 1. Main Search
        response = client.search(
            query=search_query,
            search_depth="advanced",
            topic=tavily_topic,
            include_answer=tavily_answer,
            max_results=5,
            include_domains=target_domains
        )
        
        results = response.get("results", [])
        ai_summary = response.get("answer", "관련 요약 내용을 생성할 수 없습니다.")
        
        # 2. Fallback Search (Global)
        if not results:
             print(f"[Fallback] No results in category '{category}'. Switching to global search.")
             fb_response = client.search(
                query=search_query, 
                search_depth="basic",
                topic=tavily_topic,
                include_answer=tavily_answer,
                max_results=3
            )
             results.extend(fb_response.get("results", []))
             if not ai_summary or ai_summary == "관련 요약 내용을 생성할 수 없습니다.":
                 ai_summary = fb_response.get("answer")

        # 3. Format Response
        user_response_items = []
        for res in results:
            domain = _extract_domain(res.get("url", ""))
            clean_title = _clean_text(res.get("title"))
            final_title = f"{clean_title} | {domain}" if domain else clean_title

            item = {
                "title": final_title,
                "link": res.get("url"),
                "summary": _clean_text(res.get("content", ""))[:800] + "...",
                "tags": search_terms,
                "collected_at": datetime.utcnow().isoformat()
            }
            user_response_items.append(item)
            
        # 4. Background Archiving
        if results:
            thread = threading.Thread(
                target=_process_and_save_background, 
                args=(results, search_terms, category)
            )
            thread.start()
            
        # 최종 반환: 요약 답변과 검색 결과 리스트를 딕셔너리로 묶어서 반환
        return {
            "answer": ai_summary,
            "items": user_response_items[:5],
            "category": category
        }

    except Exception as e:
        return {
            "answer": f"검색 중 오류가 발생했습니다: {str(e)}",
            "items": [{"title": "Search Error", "link": "", "summary": str(e)}],
            "category": category
        }

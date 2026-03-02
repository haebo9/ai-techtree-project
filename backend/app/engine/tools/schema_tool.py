from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# ==========================================
# 1. Track Tool Schemas (get_techtree_track)
# ==========================================
class TrackItem(BaseModel):
    track_name: str = Field(description="Name of the AI track")
    description: str = Field(description="Brief overview of what this track covers.")

class TrackOutput(BaseModel):
    # Case A: List all tracks
    message: Optional[str] = Field(None, description="Message displayed when listing all available tracks.")
    available_tracks: Optional[List[TrackItem]] = Field(None, description="List of all available tracks in the system.")

    # Case B: Semantic Recommendation
    recommended_track: Optional[str] = Field(None, description="The name of the best-matching track based on user interests.")
    description: Optional[str] = Field(None, description="Description of the recommended track.")
    matching_score: Optional[float] = Field(None, description="Similarity score (0.0 to 1.0) indicating how well the track matches user interests.")
    reason: Optional[str] = Field(None, description="Explanation of why this track was recommended.")
    track_content: Optional[Dict[str, Any]] = Field(None, description="Summary of the track content, including key steps and topics. Use this to give a high-level overview.")

    # Common
    error: Optional[str] = Field(None, description="Error message if the operation failed.")

# ==========================================
# 2. Path Tool Schemas (get_techtree_path)
# ==========================================
class PathNode(BaseModel):
    subject: str = Field(description="Name of the subject to study.")
    category: Optional[str] = Field(None, description="Category of the subject (e.g., 'Language', 'Framework').")
    description: Optional[str] = Field(None, description="Short explanation of what this subject covers.")
    importance: str = Field("Medium", description="Importance level of the subject ('High', 'Medium', 'Low').")

class PathOutput(BaseModel):
    track: Optional[str] = Field(None, description="Name of the track for this roadmap.")
    description: Optional[str] = Field(None, description="Description of the track.")
    
    # Optimized structure: {"Step 1": [PathNode, PathNode...], "Step 2": ...}
    roadmap: Optional[Dict[str, List[PathNode]]] = Field(
        None, 
        description="Structured roadmap where keys are Step names (e.g., 'Step 1: AI Basics') and values are lists of subjects to study."
    )
    note: Optional[str] = Field(None, description="Additional notes or guidance for this roadmap.")
    
    error: Optional[str] = Field(None, description="Error message if the operation failed.")
    
    # Fuzzy / Guide
    candidates: Optional[List[str]] = Field(None, description="List of similar tracks found.")
    guide: Optional[str] = Field(None, description="Guidance for the agent if track is not found.")

# ==========================================
# 3. Trend Tool Schemas (get_techtree_trend)
# ==========================================
class TrendItem(BaseModel):
    title: str = Field(description="Title of the article or resource.")
    link: str = Field(description="URL link to the resource.")
    summary: str = Field(description="Brief summary of the content.")
    tags: List[str] = Field(description="Keywords or tags related to the content.")
    # collected_at: Optional[str] = Field(None, description="ISO timestamp when this item was collected.")

class TrendOutput(BaseModel):
    answer: str = Field(description="AI-generated summary/insight synthesizing the search results to answer the user's query.")
    items: List[TrendItem] = Field(description="List of raw search results (articles, papers, repos) used to generate the answer.")
    category: str = Field(description="Category of the search (e.g., 'tech_news', 'research').")
    
    error: Optional[str] = Field(None, description="Error message if the operation failed.")

# ==========================================
# 4. Subject Tool Schemas (get_techtree_subject)
# ==========================================
class SubjectOutput(BaseModel):
    subject: Optional[str] = Field(None, description="The specific subject being queried.")
    track: Optional[str] = Field(None, description="The track this subject belongs to.")
    category: Optional[str] = Field(None, description="The category of the subject.")
    
    # Details contains nested structure (Lv1, Lv2, Lv3 lists)
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Detailed learning concepts organized by levels (e.g., {'Lv1': [...], 'Lv2': [...]})."
    )

    # Fuzzy Search / Guidance
    message: Optional[str] = Field(None, description="Suggestion message when exact match is not found.")
    candidates: Optional[List[str]] = Field(None, description="List of similar subjects found.")
    guide: Optional[str] = Field(None, description="Guidance instruction for the Agent on what to do next (e.g., use another tool).")
    
    error: Optional[str] = Field(None, description="Error message if the operation failed.")

# ==========================================
# 5. Survey Tool Schemas (get_techtree_survey)
# ==========================================
class SurveyOption(BaseModel):
    label: str = Field(description="Text displayed for this option.")
    value: Dict[str, Any] = Field(description="Mapping value (e.g., {'level': 'beginner'} or {'interest': ['llm', 'langchain']}).")

class SurveyQuestion(BaseModel):
    id: str = Field(description="Unique identifier for the question.")
    text: str = Field(description="The question text.")
    options: List[SurveyOption] = Field(description="List of choices for this question.")

class SurveyOutput(BaseModel):
    intro_message: str = Field(description="Greeting message to explain why the survey is being conducted.")
    questions: List[SurveyQuestion] = Field(description="List of survey questions to assess user background and interests.")

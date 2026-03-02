from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# ==========================================
# Schema (Integrated)
# ==========================================
class KeywordAndQuiz(BaseModel):
    """
    Content generated for a specific keyword, including explanation and assessment.
    """
    keyword: str = Field(description="The keyword being explained")
    
    # Content Part (Tutor)
    definition: str = Field(description="A precise, academic definition (1-2 sentences).")
    summary: str = Field(description="A easy-to-understand summary for a learner using analogies if helpful.")
    core_concepts: List[str] = Field(description="3-5 key concepts associated with this keyword.")
    
    # Assessment Part (Quiz)
    quiz_question: str = Field(description="A single technical question to test understanding of the keyword.")
    quiz_options: Optional[List[str]] = Field(description="For multiple choice, list options. Empty if open-ended.")
    quiz_answer: str = Field(description="The correct answer and brief explanation.")

# ==========================================
# Explanation Only Generation
# ==========================================
class ExplanationGeneration(BaseModel):
    """
    Content generated for a specific keyword (Tutor only, no quiz).
    """
    keyword: str = Field(description="The canonical, industry-standard name for the keyword (e.g. DP -> Dynamic Programming, but API -> API).")
    definition: str = Field(description="A precise, academic definition (1-2 sentences).")
    summary: str = Field(description="A easy-to-understand summary for a learner using analogies if helpful.")
    core_concepts: List[str] = Field(description="3-5 key concepts associated with this keyword.")

# ==========================================
# Quiz Only Generation
# ==========================================
class QuizGeneration(BaseModel):
    quiz_question: str = Field(description="A single technical question to test understanding of the keyword.")
    quiz_options: Optional[List[str]] = Field(description="For multiple choice, list options. Empty if open-ended.")
    quiz_answer: str = Field(description="The correct answer and brief explanation.")

# ==========================================
# Check Result
# ==========================================
class CheckResult(BaseModel):
    grade: Literal["fail", "pass", "perfect"] = Field(description="fail for incorrect, pass for partially correct/acceptable, perfect for completely correct.")
    feedback: str = Field(description="Brief feedback explaining the grade in Korean. And explain why it is correct or incorrect.")
    correct_answer: str = Field(description="The correct answer based on the model answer.")

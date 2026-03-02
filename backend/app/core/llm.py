from langchain_openai import ChatOpenAI
from functools import lru_cache
from app.core.config import settings

@lru_cache(maxsize=1)
def get_llm(model_name: str = "gpt-4.1", temperature: float = 0.5) -> ChatOpenAI:
    """
    Returns a cached instance of ChatOpenAI built with the given parameters.
    Default model is gpt-4.1 or we can read from settings.
    """
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY
    )

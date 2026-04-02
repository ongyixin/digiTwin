from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider


def get_llm_provider() -> LLMProvider:
    from app.config import settings
    if settings.llm_provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            chat_model=settings.chat_model,
            embedding_model=settings.embedding_model,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

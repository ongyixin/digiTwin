from functools import lru_cache

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings
from app.llm.base import LLMProvider


@lru_cache
def get_neo4j_driver() -> AsyncDriver:
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


@lru_cache
def get_llm_provider_cached() -> LLMProvider:
    from app.llm import get_llm_provider
    return get_llm_provider()


async def get_driver() -> AsyncDriver:
    return get_neo4j_driver()


async def get_llm() -> LLMProvider:
    return get_llm_provider_cached()

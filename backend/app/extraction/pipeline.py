"""Schema-guided KG extraction pipeline adapters for digiTwin.

Provides:
- GeminiLLMAdapter: wraps our LLMProvider as a neo4j-graphrag LLMInterface
- GeminiEmbedderAdapter: wraps our LLMProvider as a neo4j-graphrag Embedder
- build_kg_pipeline: factory that creates a SimpleKGPipeline with the digiTwin schema
"""

import asyncio
from typing import Optional, Union

from neo4j import AsyncDriver, Driver
from neo4j_graphrag.embeddings.base import Embedder
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm.base import LLMInterface
from neo4j_graphrag.llm.types import LLMResponse

from app.extraction.schema import DIGITWIN_SCHEMA
from app.llm.base import GenerateConfig, LLMProvider


class GeminiLLMAdapter(LLMInterface):
    """Adapts our async LLMProvider to neo4j-graphrag's sync LLMInterface."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def invoke(
        self,
        input: str,
        message_history=None,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        full_prompt = f"{system_instruction}\n\n{input}" if system_instruction else input
        # neo4j-graphrag's pipeline calls invoke() synchronously; bridge to async.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self._provider.generate(full_prompt, GenerateConfig(temperature=0.1)),
                    )
                    text = future.result()
            else:
                text = loop.run_until_complete(
                    self._provider.generate(full_prompt, GenerateConfig(temperature=0.1))
                )
        except Exception as e:
            text = f"Error: {e}"
        return LLMResponse(content=text)

    async def ainvoke(
        self,
        input: str,
        message_history=None,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        full_prompt = f"{system_instruction}\n\n{input}" if system_instruction else input
        text = await self._provider.generate(full_prompt, GenerateConfig(temperature=0.1))
        return LLMResponse(content=text)


class GeminiEmbedderAdapter(Embedder):
    """Adapts our async LLMProvider to neo4j-graphrag's sync Embedder."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def embed_query(self, text: str) -> list[float]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._provider.embed(text))
                    return future.result() or []
            else:
                return loop.run_until_complete(self._provider.embed(text)) or []
        except Exception:
            return []


def build_kg_pipeline(driver: AsyncDriver, provider: LLMProvider) -> SimpleKGPipeline:
    """Create a SimpleKGPipeline with the digiTwin schema and Gemini adapters.

    Note: SimpleKGPipeline expects a sync neo4j.Driver. We pass a compatible
    session-level driver; for async usage, run_async() is called directly.
    """
    llm_adapter = GeminiLLMAdapter(provider)
    embedder_adapter = GeminiEmbedderAdapter(provider)

    return SimpleKGPipeline(
        llm=llm_adapter,
        driver=driver,
        embedder=embedder_adapter,
        schema=DIGITWIN_SCHEMA,
        from_pdf=False,
        perform_entity_resolution=True,
        on_error="IGNORE",
    )

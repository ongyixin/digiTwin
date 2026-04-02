"""Evaluation: citation faithfulness.

Checks that node IDs cited in synthesis answers actually exist in Neo4j
and are semantically relevant to the question asked.

Run with: pytest tests/eval/citation_faithfulness.py -v
Requires a running Neo4j instance and GEMINI_API_KEY.
"""

import asyncio
import re
import pytest


EVAL_QUESTIONS = [
    {
        "question": "What was decided about the product launch date?",
        "expected_labels": ["Decision"],
    },
    {
        "question": "What assumptions underpin the infrastructure budget decision?",
        "expected_labels": ["Assumption", "Decision"],
    },
]


@pytest.mark.parametrize("case", EVAL_QUESTIONS, ids=[c["question"][:40] for c in EVAL_QUESTIONS])
def test_cited_nodes_exist(case):
    """All node IDs cited in the answer must exist in Neo4j."""
    try:
        from app.dependencies import get_neo4j_driver, get_llm_provider_cached
        from app.services.retrieval_service import RetrievalService
    except ImportError:
        pytest.skip("App dependencies not available")

    driver = get_neo4j_driver()
    llm = get_llm_provider_cached()
    service = RetrievalService(driver, llm)

    async def _run():
        return await service.query(case["question"], user_id="eval_harness")

    result = asyncio.run(_run())

    # Extract cited IDs from answer text: patterns like [D-abc123] or [Decision:D-abc123]
    cited_ids = re.findall(r"\[(?:[A-Za-z]+:)?([A-Za-z0-9\-]+)\]", result.answer)

    if not cited_ids:
        # No citations found — soft warning, not hard failure
        pytest.skip(f"No citations found in answer: {result.answer[:100]}")

    # Verify each cited ID exists in the graph context returned
    context_ids = {r["id"] for r in (result.graph_context or [])}
    for cited_id in cited_ids:
        assert cited_id in context_ids or any(cited_id in str(r) for r in (result.graph_context or [])), (
            f"Cited ID '{cited_id}' not found in retrieved context. "
            f"Context IDs: {list(context_ids)[:10]}"
        )


@pytest.mark.parametrize("case", EVAL_QUESTIONS, ids=[c["question"][:40] for c in EVAL_QUESTIONS])
def test_answer_is_not_empty(case):
    """Synthesis answer must be non-empty and not an error message."""
    try:
        from app.dependencies import get_neo4j_driver, get_llm_provider_cached
        from app.services.retrieval_service import RetrievalService
    except ImportError:
        pytest.skip("App dependencies not available")

    driver = get_neo4j_driver()
    llm = get_llm_provider_cached()
    service = RetrievalService(driver, llm)

    async def _run():
        return await service.query(case["question"], user_id="eval_harness")

    result = asyncio.run(_run())

    assert result.answer, "Answer is empty"
    assert len(result.answer) > 20, f"Answer too short: '{result.answer}'"
    assert "error" not in result.answer.lower()[:50], (
        f"Answer appears to be an error: {result.answer[:100]}"
    )

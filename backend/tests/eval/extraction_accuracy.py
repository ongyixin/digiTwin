"""Evaluation: extraction accuracy.

Measures how well the LLM extracts decisions from known transcripts
against a gold standard label set.

Run with: pytest tests/eval/extraction_accuracy.py -v
Or: make eval

Requires GEMINI_API_KEY and a running environment.
"""

import asyncio
import pytest
from typing import Any

from tests.eval.gold_set import GOLD_TRANSCRIPTS, GoldDecision


def _title_matches(extracted_title: str, gold: GoldDecision) -> bool:
    """Check if an extracted title covers any gold keyword."""
    title_lower = extracted_title.lower()
    return any(kw.lower() in title_lower for kw in gold.keywords)


def _precision_recall(extracted: list[str], gold: list[GoldDecision]) -> tuple[float, float]:
    true_positives = sum(
        1 for g in gold if any(_title_matches(e, g) for e in extracted)
    )
    precision = true_positives / len(extracted) if extracted else 0.0
    recall = true_positives / len(gold) if gold else 1.0
    return precision, recall


@pytest.mark.parametrize("transcript_fixture", GOLD_TRANSCRIPTS, ids=[t.name for t in GOLD_TRANSCRIPTS])
def test_decision_extraction_recall(transcript_fixture, tmp_path, monkeypatch):
    """Extracted decisions must match gold decisions with recall >= 0.7."""
    try:
        from app.config import settings
        from app.llm import get_llm_provider
    except ImportError:
        pytest.skip("App dependencies not available")

    llm = get_llm_provider()

    async def _run():
        from app.services.ingestion_service import IngestionService

        class FakeDriver:
            pass

        svc = IngestionService(FakeDriver(), llm)  # type: ignore
        result = await svc.extract_entities_from_chunk(
            chunk=transcript_fixture.text,
            meeting_title="eval",
            meeting_date="2026-01-01",
            participants="Alex, Jordan, Riley, Sam",
        )
        return result

    result = asyncio.run(_run())
    extracted_titles = [d.get("title", "") for d in result.get("decisions", [])]

    _, recall = _precision_recall(extracted_titles, transcript_fixture.expected_decisions)

    assert recall >= 0.7, (
        f"[{transcript_fixture.name}] Decision recall {recall:.2f} < 0.7. "
        f"Expected titles matching {[g.keywords for g in transcript_fixture.expected_decisions]}, "
        f"got: {extracted_titles}"
    )


@pytest.mark.parametrize("transcript_fixture", GOLD_TRANSCRIPTS, ids=[t.name for t in GOLD_TRANSCRIPTS])
def test_assumption_extraction_present(transcript_fixture):
    """If gold set expects assumptions, at least 1 should be extracted."""
    if transcript_fixture.expected_assumption_count == 0:
        pytest.skip("No assumptions expected in this gold fixture")

    try:
        from app.config import settings
        from app.llm import get_llm_provider
    except ImportError:
        pytest.skip("App dependencies not available")

    llm = get_llm_provider()

    async def _run():
        from app.services.ingestion_service import IngestionService

        class FakeDriver:
            pass

        svc = IngestionService(FakeDriver(), llm)  # type: ignore
        return await svc.extract_entities_from_chunk(
            chunk=transcript_fixture.text,
            meeting_title="eval",
            meeting_date="2026-01-01",
            participants="Alex, Jordan, Riley, Sam",
        )

    result = asyncio.run(_run())
    assumptions = result.get("assumptions", [])
    assert len(assumptions) >= 1, (
        f"[{transcript_fixture.name}] Expected ≥1 assumption, got {len(assumptions)}"
    )

"""
CLI tool: ingest the sample transcript directly (bypasses HTTP API).
Usage: python scripts/run_ingestion.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from neo4j import AsyncGraphDatabase
from google import genai

from app.config import settings
from app.services.ingestion_service import IngestionService


async def main():
    transcript_path = os.path.join(os.path.dirname(__file__), "../data/sample_transcript.txt")
    with open(transcript_path) as f:
        transcript = f.read()

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    gemini = genai.Client(api_key=settings.gemini_api_key)

    service = IngestionService(driver, gemini)
    result = await service.ingest_transcript(
        transcript=transcript,
        meeting_title="Beta Launch Review",
        meeting_date="2026-04-01",
        participants=["Alex Chen", "Jordan Lee", "Sam Patel", "Riley Kim"],
    )

    print(f"Meeting ID: {result.meeting_id}")
    print(f"Entities created: {result.entities_created}")
    print(f"Decision IDs: {result.decision_ids}")

    await driver.close()


if __name__ == "__main__":
    asyncio.run(main())

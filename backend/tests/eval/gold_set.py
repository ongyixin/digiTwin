"""Gold standard transcripts and expected extractions for the evaluation harness.

In production, load these from a JSON file or a dedicated evaluation dataset.
Here we define a small inline fixture to bootstrap the harness.
"""

from dataclasses import dataclass, field


@dataclass
class GoldDecision:
    title: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class GoldTranscript:
    name: str
    text: str
    expected_decisions: list[GoldDecision]
    expected_assumption_count: int = 0


GOLD_TRANSCRIPTS: list[GoldTranscript] = [
    GoldTranscript(
        name="product_launch_meeting",
        text="""
Alex: We've decided to move the product launch date to Q3 2026 to allow more testing time.
Jordan: I agree. We're assuming the QA team can complete full regression testing in 6 weeks.
Alex: The decision is based on the latest performance benchmark report which shows the system handles 10k concurrent users.
Sam: I'll create a task to update the marketing materials by next Friday.
""",
        expected_decisions=[
            GoldDecision(
                title="Move product launch to Q3 2026",
                keywords=["launch", "Q3", "2026"],
            ),
        ],
        expected_assumption_count=1,
    ),
    GoldTranscript(
        name="budget_review",
        text="""
Riley: We've approved the $2M budget increase for the infrastructure upgrade.
Alex: The decision depends on the assumption that cloud costs won't exceed 15% of the new allocation.
Jordan: All procurement decisions over $500k require VP approval as per our policy.
""",
        expected_decisions=[
            GoldDecision(
                title="Approve $2M budget increase",
                keywords=["budget", "infrastructure", "2M"],
            ),
        ],
        expected_assumption_count=1,
    ),
]

"""PII detection and redaction for pre-index sensitivity classification.

Uses regex patterns for common PII types (email, phone, SSN, credit card)
and a configurable keyword list for domain-specific sensitivity.
Set PII_REDACTION_ENABLED=true in the environment to activate redaction.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PIIResult:
    redacted_text: str
    sensitivity_level: str  # "public" | "internal" | "confidential" | "restricted"
    pii_types_detected: list[str] = field(default_factory=list)
    hit_count: int = 0


# Regex patterns for common PII
_PATTERNS: list[tuple[str, str, str]] = [
    # (label, pattern, replacement)
    ("email", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
    ("phone", r"\b(?:\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b", "[PHONE]"),
    ("ssn", r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    ("credit_card", r"\b(?:\d{4}[\s\-]?){3}\d{4}\b", "[CARD]"),
    ("ip_address", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP]"),
    ("api_key", r"\b(?:sk|pk|api|key|token)[-_][A-Za-z0-9]{16,}\b", "[API_KEY]"),
]

# Sensitivity keywords that escalate classification
_SENSITIVITY_KEYWORDS = {
    "restricted": {"salary", "compensation", "termination", "layoff", "lawsuit", "acquisition",
                   "merger", "insider", "classified"},
    "confidential": {"revenue", "forecast", "roadmap", "nda", "confidential", "proprietary",
                     "trade secret", "customer data", "pii", "gdpr", "hipaa"},
    "internal": {"internal", "draft", "wip", "unreleased", "pre-release"},
}


class PIIService:
    def __init__(self, redaction_enabled: bool = False) -> None:
        self._redaction_enabled = redaction_enabled

    def classify_sensitivity(self, text: str) -> str:
        """Classify the sensitivity level of text without redacting."""
        lower = text.lower()
        for level in ("restricted", "confidential", "internal"):
            for kw in _SENSITIVITY_KEYWORDS[level]:
                if kw in lower:
                    return level
        # Check for PII patterns — presence alone bumps to confidential
        for label, pattern, _ in _PATTERNS:
            if re.search(pattern, text):
                return "confidential"
        return "public"

    def scan_and_redact(self, text: str) -> PIIResult:
        """Detect PII, classify sensitivity, and optionally redact."""
        detected: list[str] = []
        redacted = text
        hit_count = 0

        for label, pattern, replacement in _PATTERNS:
            matches = re.findall(pattern, redacted)
            if matches:
                detected.append(label)
                hit_count += len(matches)
                if self._redaction_enabled:
                    redacted = re.sub(pattern, replacement, redacted)

        # Determine sensitivity level
        lower = text.lower()
        sensitivity = "internal"
        for level in ("restricted", "confidential", "internal"):
            for kw in _SENSITIVITY_KEYWORDS[level]:
                if kw in lower:
                    sensitivity = level
                    break
        if detected:
            # Any PII bumps minimum to confidential
            levels = ["public", "internal", "confidential", "restricted"]
            if levels.index(sensitivity) < levels.index("confidential"):
                sensitivity = "confidential"

        return PIIResult(
            redacted_text=redacted if self._redaction_enabled else text,
            sensitivity_level=sensitivity,
            pii_types_detected=detected,
            hit_count=hit_count,
        )


_service_instance: Optional[PIIService] = None


def get_pii_service() -> PIIService:
    global _service_instance
    if _service_instance is None:
        from app.config import settings
        _service_instance = PIIService(
            redaction_enabled=getattr(settings, "pii_redaction_enabled", False)
        )
    return _service_instance

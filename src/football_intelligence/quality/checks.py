"""Reusable data quality check placeholders."""

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityCheckResult:
    """Result from a data quality check."""

    name: str
    passed: bool
    details: str


def run_placeholder_checks() -> list[QualityCheckResult]:
    """Return placeholder quality results until source checks are implemented."""

    return [
        QualityCheckResult(
            name="scaffold_available",
            passed=True,
            details="Initial repository structure is present.",
        )
    ]

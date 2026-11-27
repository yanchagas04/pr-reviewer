"""Modelos do contrato de saída.

A fonte da verdade é ``schemas/review_report.schema.json``; os testes garantem
que estes modelos não divergem dele.
"""

from copy import deepcopy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal[
    "correctness",
    "security",
    "performance",
    "error_handling",
    "maintainability",
    "complexity",
    "testing",
    "conventions",
    "regression",
    "architecture",
]
Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
Status = Literal["approve", "comment", "request_changes"]
Source = Literal["static", "ai"]

# Campos preenchidos pelo pipeline, nunca pela IA.
PIPELINE_FIELDS = ("source", "rule_id", "fingerprint")


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Finding(_Contract):
    category: Category
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    file: str = Field(min_length=1)
    line: int = Field(ge=1)
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=20)
    evidence: str = Field(min_length=1)
    impact: str = Field(min_length=10)
    suggestion: str = Field(min_length=10)
    # None significa "ausente": serialize com exclude_none=True.
    source: Source | None = None
    rule_id: str | None = None
    fingerprint: str | None = None


class ReviewReport(_Contract):
    summary: str = Field(min_length=1, max_length=4000)
    status: Status
    total_findings: int = Field(ge=0)
    findings: list[Finding]

    @model_validator(mode="after")
    def _total_matches_findings(self) -> Self:
        if self.total_findings != len(self.findings):
            raise ValueError(
                f"total_findings ({self.total_findings}) difere da quantidade "
                f"de findings ({len(self.findings)})"
            )
        return self


def to_groq_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Devolve a versão do schema enviada à Groq, sem os campos do pipeline."""
    result = deepcopy(schema)
    properties = result["$defs"]["finding"]["properties"]
    for name in PIPELINE_FIELDS:
        properties.pop(name, None)
    return result

import json
from pathlib import Path
from typing import get_args

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from pr_reviewer import models
from pr_reviewer.models import Finding, ReviewReport, to_groq_schema

SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "review_report.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
FINDING_SCHEMA = SCHEMA["$defs"]["finding"]
CONSTRAINTS = ("minLength", "maxLength", "minimum", "maximum")


def finding(**overrides):
    return {
        "category": "correctness",
        "severity": "HIGH",
        "confidence": 0.95,
        "file": "src/user_service.py",
        "line": 42,
        "title": "Possível erro no tratamento de dados",
        "description": "O retorno de users.get pode ser None neste fluxo.",
        "evidence": "user = users.get(id); user.name",
        "impact": "Exceção em tempo de execução.",
        "suggestion": "Trate o caso de usuário inexistente.",
    } | overrides


def report(findings, **overrides):
    return {
        "summary": "Resumo",
        "status": "comment",
        "total_findings": len(findings),
        "findings": findings,
    } | overrides


def test_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize(
    ("model", "schema"), [(Finding, FINDING_SCHEMA), (ReviewReport, SCHEMA)]
)
def test_model_matches_schema_structure(model, schema):
    fields = model.model_fields
    assert set(fields) == set(schema["properties"])
    assert {n for n, f in fields.items() if f.is_required()} == set(schema["required"])

    generated = model.model_json_schema()["properties"]
    for name, spec in schema["properties"].items():
        for key in CONSTRAINTS:
            assert generated[name].get(key) == spec.get(key), f"{name}.{key}"


@pytest.mark.parametrize(
    ("alias", "spec"),
    [
        (models.Category, FINDING_SCHEMA["properties"]["category"]),
        (models.Severity, FINDING_SCHEMA["properties"]["severity"]),
        (models.Source, FINDING_SCHEMA["properties"]["source"]),
        (models.Status, SCHEMA["properties"]["status"]),
    ],
)
def test_enums_match_schema(alias, spec):
    assert list(get_args(alias)) == spec["enum"]


@pytest.mark.parametrize(
    "payload",
    [
        report([]),
        report([finding()]),
        report([finding(source="static", rule_id=None, fingerprint="abc")]),
    ],
)
def test_valid_payloads_pass_both_and_round_trip(payload):
    Draft202012Validator(SCHEMA).validate(payload)
    parsed = ReviewReport.model_validate(payload)
    Draft202012Validator(SCHEMA).validate(parsed.model_dump(exclude_none=True))


@pytest.mark.parametrize(
    "bad",
    [
        {"line": 0},
        {"line": "42"},
        {"confidence": 1.5},
        {"severity": "URGENT"},
        {"title": "abc"},
        {"extra": "field"},
    ],
)
def test_invalid_findings_fail_both(bad):
    payload = report([finding(**bad)])
    assert not Draft202012Validator(SCHEMA).is_valid(payload)
    with pytest.raises(ValidationError):
        ReviewReport.model_validate(payload)


def test_total_findings_must_match():
    with pytest.raises(ValidationError, match="total_findings"):
        ReviewReport.model_validate(report([finding()], total_findings=2))


def test_groq_schema_is_strict_compatible_and_keeps_original():
    groq = to_groq_schema(SCHEMA)
    item = groq["$defs"]["finding"]

    assert set(item["properties"]) == set(item["required"])
    for node in (groq, item):
        assert node["additionalProperties"] is False
        assert set(node["properties"]) == set(node["required"])
    assert "source" in FINDING_SCHEMA["properties"]

from __future__ import annotations

from metaquery.loader import Field
from metaquery.validator import validate_v1


def _fields():
    return {
        "model_id": Field(field_id="model_id", datatable_id="MODELS", sql_expr="model_id", label="Model ID"),
        "run_date": Field(field_id="run_date", datatable_id="MODELS", sql_expr="run_date", label="Run Date"),
        "pd": Field(field_id="pd", datatable_id="MODELS", sql_expr="pd", label="Probability of Default"),
        "customer_age": Field(field_id="customer_age", datatable_id="CUSTOMERS", sql_expr="age", label="Customer Age"),
    }


def test_empty_selection_blocks():
    deduped, audit = validate_v1(_fields(), [])
    assert audit.decision == "BLOCK"
    assert audit.error["code"] == "EMPTY_SELECTION"


def test_unknown_field_blocks():
    deduped, audit = validate_v1(_fields(), ["unknown_field", "model_id"])
    assert audit.decision == "BLOCK"
    assert audit.error["code"] == "FIELD_NOT_FOUND"
    assert "unknown_field" in audit.error["unknown_field_ids"]


def test_duplicates_are_deduped_with_warning():
    deduped, audit = validate_v1(_fields(), ["model_id", "model_id", "run_date"])
    assert audit.decision == "ALLOW"
    assert deduped == ["model_id", "run_date"]
    assert any(w.get("code") == "DUPLICATE_FIELDS" for w in audit.warnings)


def test_multi_source_blocks():
    deduped, audit = validate_v1(_fields(), ["model_id", "customer_age"])
    assert audit.decision == "BLOCK"
    assert audit.error["code"] == "MULTI_SOURCE_NOT_ALLOWED"
    assert set(audit.error["sources_found"]) == {"MODELS", "CUSTOMERS"}


def test_single_source_allows():
    deduped, audit = validate_v1(_fields(), ["model_id", "pd"])
    assert audit.decision == "ALLOW"
    assert audit.source == "MODELS"
    assert audit.status == "OK"

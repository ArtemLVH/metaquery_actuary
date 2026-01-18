from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from typing import Any

from .loader import Field


SOURCE_RE = re.compile(r"^[A-Z0-9_]+$")
FIELD_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")


@dataclass
class ValidationResult:
    metaquery_version: str = "0.1.0"
    schema_version: int = 1
    timestamp: str = dc_field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    decision: str = "BLOCK"  # ALLOW or BLOCK
    status: str = "ERROR"  # OK or ERROR
    version: str = "V1"
    source: str | None = None
    fields_selected: list[str] = dc_field(default_factory=list)
    controls: dict[str, str] = dc_field(default_factory=dict)  # PASS/FAIL
    warnings: list[dict[str, Any]] = dc_field(default_factory=list)
    error: dict[str, Any] | None = None


def validate_v1(
    fields_by_id: dict[str, Field],
    selected_field_ids: list[str],
    *,
    metaquery_version: str = "0.1.0",
) -> tuple[list[str], ValidationResult]:
    """
    Returns: (deduped_selected_field_ids, ValidationResult)
    Implements SPEC (V1):
      1) non-empty selection
      2) all fields exist
      3) auto-dedupe with warning
      4) single-source constraint (CRITICAL)
      + datatable_id validation against ^[A-Z0-9_]+$
      + field_id validation against ^[A-Za-z0-9_]+$
    """
    audit = ValidationResult(metaquery_version=metaquery_version)
    audit.fields_selected = list(selected_field_ids)

    # Rule 1: Non-empty selection
    if len(selected_field_ids) == 0:
        audit.controls["non_empty_selection"] = "FAIL"
        audit.error = {
            "code": "EMPTY_SELECTION",
            "message": "No fields selected in selection.yml. At least one field is required.",
        }
        return selected_field_ids, _finalize(audit)

    audit.controls["non_empty_selection"] = "PASS"

    # Field ID format validation (basic safety)
    invalid_ids = [fid for fid in selected_field_ids if not FIELD_ID_RE.match(fid)]
    if invalid_ids:
        audit.controls["all_fields_exist"] = "FAIL"
        audit.error = {
            "code": "INVALID_FIELD_ID",
            "invalid_field_ids": invalid_ids,
            "message": "field_id must be alphanumeric + underscore only.",
        }
        return selected_field_ids, _finalize(audit)

    # Rule 3 (in spec order it's Rule 3 existence): Field existence
    unknown = [fid for fid in selected_field_ids if fid not in fields_by_id]
    if unknown:
        audit.controls["all_fields_exist"] = "FAIL"
        audit.error = {
            "code": "FIELD_NOT_FOUND",
            "unknown_field_ids": unknown,
            "available_fields": sorted(fields_by_id.keys()),
            "message": f"field_id(s) not defined in fields.yml: {', '.join(unknown)}",
        }
        return selected_field_ids, _finalize(audit)
    audit.controls["all_fields_exist"] = "PASS"

    # Rule 4: No duplicates -> auto-dedupe + warning
    deduped: list[str] = []
    seen: set[str] = set()
    duplicates: dict[str, int] = {}
    for fid in selected_field_ids:
        if fid in seen:
            duplicates[fid] = duplicates.get(fid, 1) + 1
            continue
        seen.add(fid)
        deduped.append(fid)

    if duplicates:
        audit.controls["no_duplicates"] = "PASS"
        for fid, count in duplicates.items():
            audit.warnings.append(
                {
                    "code": "DUPLICATE_FIELDS",
                    "field_id": fid,
                    "count": count,
                    "message": f"field_id '{fid}' appears {count} times. Auto-deduplicated to single occurrence.",
                }
            )
    else:
        audit.controls["no_duplicates"] = "PASS"

    # Rule 2: Single-source constraint (CRITICAL)
    sources: dict[str, list[str]] = {}
    for fid in deduped:
        src = fields_by_id[fid].datatable_id
        sources.setdefault(src, []).append(fid)

    if len(sources) != 1:
        audit.controls["single_source"] = "FAIL"
        audit.error = {
            "code": "MULTI_SOURCE_NOT_ALLOWED",
            "sources_found": sorted(sources.keys()),
            "fields_by_source": {k: v for k, v in sources.items()},
            "message": "Fields span multiple sources. V1 restriction: single-source queries only.",
            "recommendation": "Create a pre-validated view (V2) or define explicit joins (V3).",
        }
        return deduped, _finalize(audit)

    audit.controls["single_source"] = "PASS"
    only_source = next(iter(sources.keys()))

    # Security: validate datatable_id format
    if not SOURCE_RE.match(only_source):
        audit.controls["valid_source_name"] = "FAIL"
        audit.error = {
            "code": "INVALID_SOURCE_NAME",
            "source": only_source,
            "message": "datatable_id must match pattern ^[A-Z0-9_]+$",
        }
        return deduped, _finalize(audit)

    audit.controls["valid_source_name"] = "PASS"
    audit.source = only_source

    # If we got here => ALLOW
    audit.decision = "ALLOW"
    audit.status = "OK"
    audit.fields_selected = list(deduped)
    return deduped, _finalize(audit)


def _finalize(audit: ValidationResult) -> ValidationResult:
    # Derive status/decision if not already set to ALLOW/OK
    if audit.decision != "ALLOW":
        audit.decision = "BLOCK"
    if audit.status != "OK":
        audit.status = "ERROR"
    return audit

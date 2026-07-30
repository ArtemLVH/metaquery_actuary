from __future__ import annotations

from .loader import Field


def build_sql_v1(source: str, selected_field_ids: list[str], fields_by_id: dict[str, Field]) -> str:
    """
    V1 SQL: simple SELECT ... FROM <datatable_id>;
    No JOIN/WHERE/GROUP BY.
    """
    cols = [fields_by_id[fid].sql_expr for fid in selected_field_ids]
    lines = ["SELECT"]
    for i, c in enumerate(cols):
        comma = "," if i < len(cols) - 1 else ""
        lines.append(f"    {c}{comma}")
    lines.append(f"FROM {source};")
    return "\n".join(lines) + "\n"


def build_sql_v2(view_id: str, selected_field_ids: list[str], fields_by_id: dict[str, Field]) -> str:
    """V2 SQL: select governed columns from one pre-validated SQL view."""
    return build_sql_v1(view_id, selected_field_ids, fields_by_id)

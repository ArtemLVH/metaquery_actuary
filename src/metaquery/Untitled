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

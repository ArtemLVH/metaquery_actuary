from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Field:
    field_id: str
    datatable_id: str
    sql_expr: str
    label: str | None = None
    view_id: str | None = None


@dataclass(frozen=True)
class View:
    view_id: str
    status: str
    source_tables: tuple[str, ...]
    owner: str | None = None
    validated_at: str | None = None


class MetaQueryError(Exception):
    """Base error for MetaQuery."""


class YamlLoadError(MetaQueryError):
    """YAML loading/parsing error."""


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise YamlLoadError(f"File not found: {path}") from e

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise YamlLoadError(f"Invalid YAML in {path}: {e}") from e

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise YamlLoadError(f"Top-level YAML must be a mapping in {path}")
    return data


def load_fields(fields_path: str | Path) -> dict[str, Field]:
    """Load fields.yml -> dict[field_id, Field]"""
    p = Path(fields_path)
    data = _load_yaml(p)

    raw_fields = data.get("fields")
    if raw_fields is None:
        raise YamlLoadError(f"Missing 'fields' key in {p}")
    if not isinstance(raw_fields, list):
        raise YamlLoadError(f"'fields' must be a list in {p}")

    out: dict[str, Field] = {}
    for i, item in enumerate(raw_fields):
        if not isinstance(item, dict):
            raise YamlLoadError(f"fields[{i}] must be a mapping in {p}")

        field_id = item.get("field_id")
        datatable_id = item.get("datatable_id")
        sql_expr = item.get("sql_expr")
        label = item.get("label")
        view_id = item.get("view_id")

        if not isinstance(field_id, str) or not field_id.strip():
            raise YamlLoadError(f"fields[{i}].field_id must be a non-empty string in {p}")
        if not isinstance(datatable_id, str) or not datatable_id.strip():
            raise YamlLoadError(f"fields[{i}].datatable_id must be a non-empty string in {p}")
        if not isinstance(sql_expr, str) or not sql_expr.strip():
            raise YamlLoadError(f"fields[{i}].sql_expr must be a non-empty string in {p}")
        if label is not None and not isinstance(label, str):
            raise YamlLoadError(f"fields[{i}].label must be a string if provided in {p}")
        if view_id is not None and (not isinstance(view_id, str) or not view_id.strip()):
            raise YamlLoadError(f"fields[{i}].view_id must be a non-empty string if provided in {p}")

        out[field_id] = Field(
            field_id=field_id.strip(),
            datatable_id=datatable_id.strip(),
            sql_expr=sql_expr.strip(),
            label=label.strip() if isinstance(label, str) else None,
            view_id=view_id.strip() if isinstance(view_id, str) else None,
        )

    return out


def load_views(views_path: str | Path) -> dict[str, View]:
    """Load the V2 catalogue of curated SQL views."""
    p = Path(views_path)
    data = _load_yaml(p)

    raw_views = data.get("views")
    if raw_views is None:
        raise YamlLoadError(f"Missing 'views' key in {p}")
    if not isinstance(raw_views, list):
        raise YamlLoadError(f"'views' must be a list in {p}")

    out: dict[str, View] = {}
    for i, item in enumerate(raw_views):
        if not isinstance(item, dict):
            raise YamlLoadError(f"views[{i}] must be a mapping in {p}")

        view_id = item.get("view_id")
        status = item.get("status")
        source_tables = item.get("source_tables")
        owner = item.get("owner")
        validated_at = item.get("validated_at")

        if not isinstance(view_id, str) or not view_id.strip():
            raise YamlLoadError(f"views[{i}].view_id must be a non-empty string in {p}")
        if not isinstance(status, str) or not status.strip():
            raise YamlLoadError(f"views[{i}].status must be a non-empty string in {p}")
        if not isinstance(source_tables, list) or not source_tables:
            raise YamlLoadError(f"views[{i}].source_tables must be a non-empty list in {p}")
        if not all(isinstance(table, str) and table.strip() for table in source_tables):
            raise YamlLoadError(f"views[{i}].source_tables must contain non-empty strings in {p}")
        if owner is not None and not isinstance(owner, str):
            raise YamlLoadError(f"views[{i}].owner must be a string if provided in {p}")
        if validated_at is not None and not isinstance(validated_at, (str, date)):
            raise YamlLoadError(f"views[{i}].validated_at must be a date or string if provided in {p}")
        if view_id.strip() in out:
            raise YamlLoadError(f"Duplicate view_id '{view_id.strip()}' in {p}")

        out[view_id.strip()] = View(
            view_id=view_id.strip(),
            status=status.strip().upper(),
            source_tables=tuple(table.strip() for table in source_tables),
            owner=owner.strip() if isinstance(owner, str) else None,
            validated_at=str(validated_at) if validated_at is not None else None,
        )

    return out


def load_selection(selection_path: str | Path) -> list[str]:
    """Load selection.yml -> list[field_id]"""
    p = Path(selection_path)
    data = _load_yaml(p)

    raw_sel = data.get("selected_field_ids")
    if raw_sel is None:
        raise YamlLoadError(f"Missing 'selected_field_ids' key in {p}")
    if not isinstance(raw_sel, list):
        raise YamlLoadError(f"'selected_field_ids' must be a list in {p}")

    out: list[str] = []
    for i, item in enumerate(raw_sel):
        if not isinstance(item, str) or not item.strip():
            raise YamlLoadError(f"selected_field_ids[{i}] must be a non-empty string in {p}")
        out.append(item.strip())
    return out

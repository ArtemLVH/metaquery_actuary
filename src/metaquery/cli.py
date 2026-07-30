from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from .builder import build_sql_v1, build_sql_v2
from .loader import YamlLoadError, load_fields, load_selection, load_views
from .validator import validate_v1, validate_v2

app = typer.Typer(add_completion=False)
console = Console()


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@app.command()
def build(
    selection: Annotated[Path, typer.Argument(help="Path to selection.yml")],
    fields: Annotated[Path, typer.Option("--fields", help="Path to fields.yml")],
    execute: Annotated[
        bool, typer.Option("--execute", help="Execute the validated SQL on a SQLite database")
    ] = False,
    db: Annotated[
        Path | None,
        typer.Option("--db", help="Path to the SQLite database (required with --execute)"),
    ] = None,
    version: Annotated[str, typer.Option("--version", help="Governance rules: V1 or V2")] = "V1",
    views: Annotated[
        Path | None, typer.Option("--views", help="Path to views.yml (required with --version V2)")
    ] = None,
) -> None:
    """
    Build a governed SQL query from YAML inputs.
    Outputs: query.sql, audit.json, explain.txt (+ extract.csv, manifest.json avec --execute)
    """
    version = version.upper()
    if version not in {"V1", "V2"}:
        console.print(Panel("ERROR: --version doit valoir V1 ou V2", title="MetaQuery", style="red"))
        raise typer.Exit(code=2)
    if version == "V2" and views is None:
        console.print(Panel("ERROR: --views est requis avec --version V2", title="MetaQuery", style="red"))
        raise typer.Exit(code=2)

    try:
        fields_by_id = load_fields(fields)
        selected = load_selection(selection)
        views_by_id = load_views(views) if views is not None and version == "V2" else {}
    except YamlLoadError as e:
        console.print(Panel(str(e), title="YAML ERROR", style="red"))
        raise typer.Exit(code=2)

    if version == "V2":
        deduped, audit = validate_v2(fields_by_id, selected, views_by_id)
    else:
        deduped, audit = validate_v1(fields_by_id, selected)

    # Always write audit.json (even on BLOCK)
    audit_path = Path("audit.json")
    _write_json(audit_path, audit.__dict__)

    if audit.decision != "ALLOW":
        code = (audit.error or {}).get("code", "VALIDATION_ERROR")
        console.print(Panel(f"ERROR: {code}\nDecision: BLOCK", title="VALIDATION", style="red"))
        if audit.error:
            console.print(json.dumps(audit.error, indent=2, ensure_ascii=False))
        raise typer.Exit(code=1)

    # Build SQL
    if version == "V2":
        sql = build_sql_v2(audit.source or "", deduped, fields_by_id)
    else:
        sql = build_sql_v1(audit.source or "", deduped, fields_by_id)
    _write_text(Path("query.sql"), sql)

    # --- V1.1 : execution optionnelle (SQLite) ---
    if execute:
        if db is None:
            console.print(Panel("ERROR: --db est requis avec --execute", title="MetaQuery", style="red"))
            raise typer.Exit(code=3)
        from .executor import build_manifest, execute_sql, inspect_sqlite_view, write_extract
        from .quality import run_quality
        try:
            view_sha = inspect_sqlite_view(db, audit.source or "") if version == "V2" else None
            df = execute_sql(db, sql)
        except Exception as e:  # noqa: BLE001 - SQL drivers expose several exception types
            console.print(Panel(f"ERROR: EXECUTION_FAILED\n{e}", title="MetaQuery", style="red"))
            raise typer.Exit(code=3)
        output_sha, n_rows = write_extract(df, "extract.csv")
        verdict, checks = run_quality(df)
        build_manifest(fields_path=fields, sql=sql, source=audit.source or "",
                       executed=True, output_file="extract.csv",
                       output_sha256=output_sha, row_count=n_rows,
                       quality_verdict=verdict, quality_checks=checks,
                       governance_version=version, view_definition_sha256=view_sha)
        style = {"PASS": "green", "WARN": "yellow", "BLOCK": "red"}[verdict]
        console.print(Panel(f"EXECUTED: {n_rows} lignes -> extract.csv\nQualite: {verdict}\nManifeste: manifest.json",
                            title=f"MetaQuery {version}", style=style))
        if verdict == "BLOCK":
            raise typer.Exit(code=4)

    # Explain
    explain = []
    explain.append(f"MetaQuery {version} Validation Report")
    explain.append("==============================")
    explain.append(f"Decision: {audit.decision}")
    explain.append(f"Status: {audit.status}")
    explain.append(f"Source: {audit.source}")
    explain.append(f"Fields: {len(deduped)} selected")
    explain.append("")
    explain.append("Controls:")
    for k, v in audit.controls.items():
        mark = "✓" if v == "PASS" else "✗"
        explain.append(f"  {mark} {k}")
    if audit.warnings:
        explain.append("")
        explain.append("Warnings:")
        for w in audit.warnings:
            explain.append(f"  - {w.get('code')}: {w.get('message')}")
    explain.append("")
    explain.append("Generated SQL:")
    explain.append("--------------")
    explain.append(sql.rstrip("\n"))
    explain.append("")

    _write_text(Path("explain.txt"), "\n".join(explain))

    console.print(Panel("OK: query.sql + audit.json + explain.txt generated", title="MetaQuery", style="green"))
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()

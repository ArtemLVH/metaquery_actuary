from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .builder import build_sql_v1
from .loader import YamlLoadError, load_fields, load_selection
from .validator import validate_v1

app = typer.Typer(add_completion=False)
console = Console()


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@app.command()
def build(
    selection: Path = typer.Argument(..., help="Path to selection.yml"),
    fields: Path = typer.Option(..., "--fields", help="Path to fields.yml"),
    execute: bool = typer.Option(False, "--execute", help="Execute the validated SQL on a SQLite database"),
    db: Path = typer.Option(None, "--db", help="Path to the SQLite database (required with --execute)"),
) -> None:
    """
    Build a governed SQL query (V1) from YAML inputs.
    Outputs: query.sql, audit.json, explain.txt (+ extract.csv, manifest.json avec --execute)
    """
    try:
        fields_by_id = load_fields(fields)
        selected = load_selection(selection)
    except YamlLoadError as e:
        console.print(Panel(str(e), title="YAML ERROR", style="red"))
        raise typer.Exit(code=2)

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
    sql = build_sql_v1(audit.source or "", deduped, fields_by_id)
    _write_text(Path("query.sql"), sql)

    # --- V1.1 : execution optionnelle (SQLite) ---
    if execute:
        if db is None:
            console.print(Panel("ERROR: --db est requis avec --execute", title="MetaQuery", style="red"))
            raise typer.Exit(code=3)
        from .executor import execute_sql, write_extract, build_manifest
        from .quality import run_quality
        try:
            df = execute_sql(db, sql)
        except Exception as e:
            console.print(Panel(f"ERROR: EXECUTION_FAILED\n{e}", title="MetaQuery", style="red"))
            raise typer.Exit(code=3)
        output_sha, n_rows = write_extract(df, "extract.csv")
        verdict, checks = run_quality(df)
        build_manifest(fields_path=fields, sql=sql, source=audit.source or "",
                       executed=True, output_file="extract.csv",
                       output_sha256=output_sha, row_count=n_rows,
                       quality_verdict=verdict, quality_checks=checks)
        style = {"PASS": "green", "WARN": "yellow", "BLOCK": "red"}[verdict]
        console.print(Panel(f"EXECUTED: {n_rows} lignes -> extract.csv\nQualite: {verdict}\nManifeste: manifest.json",
                            title="MetaQuery V1.1", style=style))
        if verdict == "BLOCK":
            raise typer.Exit(code=4)

    # Explain
    explain = []
    explain.append("MetaQuery V1 Validation Report")
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
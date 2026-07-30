"""V1.1 — exécution SQLite + manifeste de traçabilité."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

import pandas as pd
import yaml


def execute_sql(db_path, sql: str) -> pd.DataFrame:
    """Exécute la requête sur la base SQLite et retourne un DataFrame."""
    con = sqlite3.connect(str(db_path))
    try:
        return pd.read_sql(sql, con)
    finally:
        con.close()


def inspect_sqlite_view(db_path, view_id: str) -> str:
    """Require a real SQLite VIEW and return the SHA-256 of its stored definition."""
    con = sqlite3.connect(str(db_path))
    try:
        row = con.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'view' AND name = ?",
            (view_id,),
        ).fetchone()
    finally:
        con.close()
    if row is None or not row[0]:
        raise ValueError(
            f"VIEW_NOT_FOUND_IN_DATABASE: '{view_id}' must exist as a SQLite VIEW, not a table"
        )
    return hashlib.sha256(row[0].encode("utf-8")).hexdigest()


def write_extract(df: pd.DataFrame, out_path: str = "extract.csv"):
    """Écrit le CSV et retourne (sha256_hex, nb_lignes)."""
    df.to_csv(out_path, index=False)
    sha = hashlib.sha256(Path(out_path).read_bytes()).hexdigest()
    return sha, len(df)


def build_manifest(fields_path, sql: str, source: str, executed: bool,
                   output_file=None, output_sha256=None, row_count=None,
                   quality_verdict=None, quality_checks=None, out: str = "manifest.json",
                   governance_version: str = "V1.1", view_definition_sha256=None):
    """FOURNI — assemble le manifeste (relit fields.yml lui-même)."""
    raw = yaml.safe_load(Path(fields_path).read_text(encoding="utf-8"))
    dictionnaire = {
        f["field_id"]: {
            "label": f.get("label"),
            "table": f["datatable_id"],
            "view": f.get("view_id"),
            "sql_expr": f["sql_expr"],
        }
        for f in raw.get("fields", [])
    }
    manifest = {
        "producteur": f"metaquery_actuary {governance_version}",
        "horodatage": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "statut_requete": "executee" if executed else "generee_validee",
        "source": source,
        "vue_sql_sha256": view_definition_sha256,
        "requete": sql,
        "dictionnaire": dictionnaire,
        "extraction": {"fichier": output_file, "lignes": row_count, "sha256": output_sha256},
        "qualite": {"verdict": quality_verdict, "controles": quality_checks},
    }
    Path(out).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest

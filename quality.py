# -*- coding: utf-8 -*-
"""V1.1 — porte de qualité sur l'extraction : PASS / WARN / BLOCK."""
import pandas as pd


def run_quality(df: pd.DataFrame):
    """Retourne (verdict, checks) : trois contrôles R0/R1 automatisés."""
    checks = {}
    checks["non_empty_extract"] = "PASS" if len(df) > 0 else "BLOCK"
    if len(df) > 0:
        for col in df.columns:
            if df[col].isna().mean() >= 0.20:
                checks[f"null_rate_{col}"] = "WARN"
        if df.duplicated().sum() > 0:
            checks["duplicated_rows"] = "WARN"

    # --- agrégation : ne pas modifier ---
    if "BLOCK" in checks.values():
        verdict = "BLOCK"
    elif "WARN" in checks.values():
        verdict = "WARN"
    else:
        verdict = "PASS"
    return verdict, checks
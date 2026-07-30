# MetaQuery Actuary

**Field-level SQL governance for model validation, auditability, and controlled data extraction**  
*An actuarial approach to data quality and model risk.*

---

## Why this project exists

In actuarial, risk, and data contexts, the main risk is often **not the model itself**, but the **data extraction logic** used upstream.

**Common issues:**
- Manual SQL → human errors
- Implicit multi-source joins → row explosion
- Silent data inconsistencies → biased models
- No traceability → impossible audits

A validated model is meaningless if the **data extraction is not governed**.

---

## Core idea

MetaQuery separates **what is allowed** from **what is used**.

- A governed **field dictionary** defines which fields exist and where they come from
- A simple **selection file** defines which fields are used for a given analysis
- SQL is generated **only if governance rules are respected**

This makes data extraction:
- Explicit
- Reproducible
- Auditable

---

## How it works

### 1. Define allowed fields (`fields.yml`)

Each field is declared once with:
- A stable logical identifier (`field_id`)
- An explicit data source (`datatable_id`)
- The corresponding SQL expression (`sql_expr`)

**Example:**
```yaml
fields:
  - field_id: model_id
    label: Model ID
    datatable_id: MODELS
    sql_expr: model_id

  - field_id: pd
    label: Probability of Default
    datatable_id: MODELS
    sql_expr: pd

  - field_id: customer_age
    label: Customer Age
    datatable_id: CUSTOMERS
    sql_expr: age
```

---

### 2. Select fields for a use case (`selection.yml`)

For each model, report, or analysis, a selection file lists the required fields by ID.

**Example (valid V1):**
```yaml
selected_field_ids:
  - model_id
  - pd
```

**Generated SQL:**
```sql
SELECT
    model_id,
    pd
FROM MODELS;
```

---

**Example (rejected in V1):**
```yaml
selected_field_ids:
  - model_id      # source: MODELS
  - customer_age  # source: CUSTOMERS
```

**Error message:**
```
ERROR: MULTI_SOURCE_NOT_ALLOWED

Fields span multiple sources:
  - MODELS: model_id
  - CUSTOMERS: customer_age

V1 restriction: single-source queries only
```

---

### 3. Apply governance rules

Selections are validated against explicit rules before any SQL is produced.

See [SPEC.md](SPEC.md) for detailed validation logic.

---

## Governance strategy (risk-based)

### V1 — Single-source only 
- All selected fields must come from the same source
- Any multi-source selection is **blocked**
- Goal: eliminate implicit joins and row explosion risk

### V2 — Pre-validated views 
- Multi-source fields are allowed only through one common curated SQL view
- `views.yml` records the view status, owner, validation date, and covered source tables
- Execution verifies that the SQLite object is a real `VIEW`
- The manifest seals both the extract and the stored SQL view definition with SHA-256

### V3 — Explicit join mapping 
- Joins defined explicitly with keys and cardinality rules
- Additional controls on row multiplication and integrity

---

## Outputs (implemented)

For each valid selection:
- `query.sql` — Generated SQL
- `audit.json` — Machine-readable validation report
- `explain.txt` — Human-readable summary
- `extract.csv` — Executed and sealed extraction (with `--execute`)
- `manifest.json` — Source, dictionary, quality verdict, and SHA-256 hashes

---

## V2 retirement demo

V2 keeps the join outside the generated query. MetaQuery selects governed fields
from `VW_PORTEFEUILLE_RETRAITE`; the curated view owns the join between
`SALARIES` and `CONTRATS_RETRAITE`.

```powershell
python tools/build_db_v2.py portefeuille_v2.db

python -m metaquery.cli examples/selection_v2_retraite.yml `
  --fields examples/fields_v2_retraite.yml `
  --version V2 `
  --views examples/views_v2.yml `
  --execute `
  --db portefeuille_v2.db
```

Expected result:

```text
MetaQuery V2
EXECUTED: 3 lignes -> extract.csv
Qualite: PASS
```

Generated SQL:

```sql
SELECT
    id_salarie,
    age,
    categorie,
    salaire,
    produit,
    encours,
    age_liquidation
FROM VW_PORTEFEUILLE_RETRAITE;
```

There is deliberately no `JOIN` in `query.sql`: V2 users may consume an approved
view, but they may not invent join logic. Explicit joins remain a V3 concern.

---

## Example use cases

**Model validation:** Ensure production data extraction matches validated assumptions

**Regulatory / audit context:** Reproduce exactly how a metric was computed months later

**Data & ML pipelines:** Enforce consistent feature definitions across teams

---

## Current Status

**V2 implemented — 14 passing tests**
- Complete specification incl. V1.1 ([SPEC.md](SPEC.md))
- Example YAML files ([examples/](examples/))
- Project structure & tooling config
- Python implementation: validation, execution, quality gate (src/metaquery)
- V2 catalogue of pre-validated views and retirement multi-source demo
- Backward compatibility: the five V1 tests still pass

**V3:** Design phase

---

## Project philosophy

This project treats AI tools as **accelerators**, not decision-makers.

- LLMs help with scaffolding and boilerplate
- Core rules, invariants, and controls are defined by the human
- The focus is on rigor, not overengineering

---

## License

MIT

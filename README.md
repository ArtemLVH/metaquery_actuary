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
- Multi-source allowed only via curated SQL views
- Join logic is centralized and validated upstream

### V3 — Explicit join mapping 
- Joins defined explicitly with keys and cardinality rules
- Additional controls on row multiplication and integrity

---

## Outputs (planned)

For each valid selection:
- `query.sql` — Generated SQL
- `audit.json` — Machine-readable validation report
- `explain.txt` — Human-readable summary

---

## Example use cases

**Model validation:** Ensure production data extraction matches validated assumptions

**Regulatory / audit context:** Reproduce exactly how a metric was computed months later

**Data & ML pipelines:** Enforce consistent feature definitions across teams

---

## Current Status

**V1:**
- Complete specification ([SPEC.md](SPEC.md))
- Example YAML files ([examples/](examples/))
- Project structure & tooling config
- Python implementation (starts in 2 days)

**V2/V3:** Design phase

---

## Project philosophy

This project treats AI tools as **accelerators**, not decision-makers.

- LLMs help with scaffolding and boilerplate
- Core rules, invariants, and controls are defined by the human
- The focus is on rigor, not overengineering

---

## License

MIT
```

**Commit message :**
```
docs: add complete project documentation

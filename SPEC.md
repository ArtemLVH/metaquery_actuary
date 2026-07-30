# MetaQuery Specification (V1 + V1.1 + V2)

## Inputs

### `fields.yml`
Defines available fields with metadata:
```yaml
fields:
  - field_id: unique_identifier
    label: Human-readable name (optional)
    datatable_id: source_table
    sql_expr: actual_column_name
```

**Field definitions:**
- `field_id`: Stable identifier (alphanumeric + underscore only)
- `label`: Optional display name for UIs and reports
- `datatable_id`: SQL source identifier (table or view name). Must match pattern `[A-Z0-9_]+`
- `sql_expr`: Column name or SQL expression used in SELECT clause

**Note:** `datatable_id` is treated as the SQL source identifier (table or view name) in V1.

---

### `selection.yml`
Lists fields to include in query:
```yaml
selected_field_ids:
  - field_id_1
  - field_id_2
  - field_id_3
```

---

## Core Rules (V1)

### Rule 1: Non-empty selection
- **Requirement:** At least one field must be selected
- **Violation:** Error `EMPTY_SELECTION`
- **Message:** "No fields selected in selection.yml. At least one field is required."

---

### Rule 2: Single-source constraint **CRITICAL**
- **Requirement:** All selected fields MUST share the same `datatable_id`
- **Violation:** Error `MULTI_SOURCE_NOT_ALLOWED`
- **Message:**
```
  ERROR: MULTI_SOURCE_NOT_ALLOWED
  Decision: BLOCK

  Fields span multiple sources:
    - MODELS: model_id, run_date
    - CUSTOMERS: customer_age

  V1 restriction: single-source queries only
  Recommendation: Create a pre-validated view (V2) or define explicit joins (V3)
```

---

### Rule 3: Field existence
- **Requirement:** All `field_id` values in selection must exist in `fields.yml`
- **Violation:** Error `FIELD_NOT_FOUND`
- **Message:**
```
  ERROR: FIELD_NOT_FOUND
  Decision: BLOCK

  field_id 'unknown_field' not defined in fields.yml
  Available fields: model_id, run_date, pd, segment, customer_age, customer_name
```

---

### Rule 4: No duplicates
- **Requirement:** Each `field_id` can appear only once in selection
- **V1 Behavior:** Auto-deduplicate + emit warning (user-friendly default)
- **Message:**
```
  WARNING: DUPLICATE_FIELDS
  field_id 'model_id' appears 2 times
  Auto-deduplicated to single occurrence
  
  Status: OK (with warnings)
```

---

## Outputs

### 1. `query.sql`
Generated SQL query:
```sql
SELECT
    field_1,
    field_2,
    field_3
FROM datatable_id;
```

**Details:**
- Column names come from `sql_expr` field in metadata
- Table name is the shared `datatable_id`
- Simple SELECT with no WHERE, JOIN, or GROUP BY in V1

---

### 2. `audit.json`
Complete validation report in JSON format:
```json
{
  "metaquery_version": "0.1.0",
  "schema_version": 1,
  "timestamp": "2026-01-14T10:30:00Z",
  "decision": "ALLOW",
  "status": "OK",
  "version": "V1",
  "source": "MODELS",
  "fields_selected": ["model_id", "run_date", "pd"],
  "controls": {
    "non_empty_selection": "PASS",
    "single_source": "PASS",
    "all_fields_exist": "PASS",
    "no_duplicates": "PASS"
  }
}
```

**Field descriptions:**
- `metaquery_version`: Tool version (semantic versioning)
- `schema_version`: Audit JSON schema version (integer, increment on breaking changes)
- `timestamp`: ISO 8601 UTC timestamp (auto-generated at validation time)
- `decision`: `ALLOW` (query can be executed) or `BLOCK` (validation failed)
- `status`: `OK` (all checks passed) or `ERROR` (at least one check failed)
- `version`: V1/V2/V3 indicator showing which rules were applied
- `source`: The `datatable_id` used (only present if single-source constraint passed)
- `fields_selected`: List of `field_id` values from selection
- `controls`: Dictionary of validation checks with PASS/FAIL status

---

### 3. `explain.txt`
Human-readable summary for documentation and audits:
```
MetaQuery V1 Validation Report
==============================
Decision: ALLOW
Status: OK
Source: MODELS
Fields: 3 selected

Controls:
  ✓ Non-empty selection
  ✓ Single-source constraint
  ✓ All fields exist in metadata
  ✓ No duplicates

Generated SQL:
--------------
SELECT
    model_id,
    run_date,
    pd
FROM MODELS;
```

---

## Complete Error Cases

### Error 1: Empty selection

**Input:**
```yaml
selected_field_ids: []
```

**Output:**
```
ERROR: EMPTY_SELECTION
Decision: BLOCK

No fields selected in selection.yml
At least one field is required
```

---

### Error 2: Multi-source rejection (CRITICAL)

**Input:**
```yaml
selected_field_ids:
  - model_id      # datatable_id: MODELS
  - customer_age  # datatable_id: CUSTOMERS
```

**Output:**
```
ERROR: MULTI_SOURCE_NOT_ALLOWED
Decision: BLOCK

Fields span multiple sources:
  - MODELS: model_id
  - CUSTOMERS: customer_age

V1 restriction: single-source queries only
Recommendation: Create a pre-validated view (V2) or define explicit joins (V3)
```

**audit.json:**
```json
{
  "metaquery_version": "0.1.0",
  "schema_version": 1,
  "timestamp": "2026-01-14T10:35:00Z",
  "decision": "BLOCK",
  "status": "ERROR",
  "version": "V1",
  "fields_selected": ["model_id", "customer_age"],
  "controls": {
    "non_empty_selection": "PASS",
    "single_source": "FAIL",
    "all_fields_exist": "PASS",
    "no_duplicates": "PASS"
  },
  "error": {
    "code": "MULTI_SOURCE_NOT_ALLOWED",
    "sources_found": ["MODELS", "CUSTOMERS"],
    "fields_by_source": {
      "MODELS": ["model_id"],
      "CUSTOMERS": ["customer_age"]
    }
  }
}
```

---

### Error 3: Unknown field

**Input:**
```yaml
selected_field_ids:
  - unknown_field
  - model_id
```

**Output:**
```
ERROR: FIELD_NOT_FOUND
Decision: BLOCK

field_id 'unknown_field' not defined in fields.yml
Available fields: model_id, run_date, pd, segment, customer_age, customer_name
```

---

### Warning 1: Duplicate fields

**Input:**
```yaml
selected_field_ids:
  - model_id
  - run_date
  - model_id
```

**Output:**
```
WARNING: DUPLICATE_FIELDS
field_id 'model_id' appears 2 times
Auto-deduplicated to single occurrence

Status: OK (with warnings)
Decision: ALLOW
```

**Generated SQL:**
```sql
SELECT
    model_id,
    run_date
FROM MODELS;
```

---

## Security & Validation

### SQL Injection Prevention

**`datatable_id` validation:**
- Must match pattern: `^[A-Z0-9_]+$`
- Invalid characters → error `INVALID_SOURCE_NAME`
- Examples:
  - Valid: `MODELS`, `RAW_DATA_2024`, `CUSTOMER_360`
  - Invalid: `models; DROP TABLE`, `data-2024`, `my table`

**`sql_expr` validation:**
- Assumed to be from trusted internal metadata (no user input in V1)
- Future versions may add expression validation

---

## Implementation Notes

### Exit Codes
- `0` — Success (validation passed, SQL generated)
- `1` — Validation error (rule violation, query blocked)
- `2` — System error (file not found, YAML parsing failed)
- `3`, `4` — introduced in V1.1, see the V1.1 section below

### Timestamps
- All timestamps in ISO 8601 UTC format
- Example: `2026-01-14T10:30:00Z`
- Generated at validation time, not at selection file creation

### YAML Parsing
- Use safe YAML loader (no arbitrary code execution)
- Clear error messages for malformed YAML
- Report line numbers for syntax errors

---

## V1.1 — Execution & Quality Gate

V1 stops at query generation. V1.1 adds optional execution on SQLite, a sealed
extract, and a post-execution quality verdict.

### Command

python -m metaquery.cli <selection.yml> --fields <fields.yml> [--execute --db <database.db>]

| Option | Type | Required | Description |
|---|---|---|---|
| `selection` | positional | yes | Path to selection.yml |
| `--fields` | path | yes | Path to fields.yml |
| `--execute` | flag | no | Execute the validated SQL on SQLite (default: off) |
| `--db` | path | with `--execute` | Path to the SQLite database |

### Pipeline

1. Load YAML (fields + selection) — failure exits 2
2. Validate against V1 rules — `audit.json` is always written; BLOCK exits 1, nothing is executed
3. Build SQL, write `query.sql`
4. *(`--execute` only)* Run the SQL on SQLite
5. Write `extract.csv`, seal it with SHA-256
6. Run the quality gate: verdict PASS / WARN / BLOCK plus per-check results
7. Write `manifest.json`
8. Write `explain.txt`, exit 0

### Outputs

| File | Written when |
|---|---|
| `audit.json` | always, including on validation BLOCK |
| `query.sql` | validation returned ALLOW |
| `extract.csv` | `--execute`, after successful execution — sealed with SHA-256 |
| `manifest.json` | `--execute` |
| `explain.txt` | end of a full run that reaches exit 0 |

`manifest.json` keys: `producteur`, `horodatage`, `statut_requete`, `source`,
`requete`, `dictionnaire`, `extraction{fichier, lignes, sha256}`,
`qualite{verdict, controles}`.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Validation BLOCK — nothing executed |
| 2 | YAML load error |
| 3 | `--db` missing with `--execute`, or SQL execution failure |
| 4 | Quality gate returned BLOCK |

### Quality gate semantics

The quality gate runs **after** execution, on the extracted data. It qualifies an
extract that already exists; it does not prevent its production.

- Validation BLOCK (exit 1) is a pre-execution gate: no query runs, no extract is written.
- Quality BLOCK (exit 4) is a post-execution verdict: `extract.csv` and `manifest.json`
  have already been written and sealed. The manifest carries the BLOCK verdict, so the
  extract remains traceable as unfit for downstream use — but a consumer must read the
  verdict, not merely check that the file exists.

### Known limitation

On exit 4, `explain.txt` is not written, because execution precedes the explain block.
A run ending in quality BLOCK leaves `audit.json`, `query.sql`, `extract.csv` and
`manifest.json`, but no explain report.

## V2 — Pre-validated views

V2 permits multi-source selections without allowing users to write joins.
Every selected field must reference one common `view_id`, and that view must be
declared with status `VALIDATED` in `views.yml`.

### Additional field metadata

```yaml
fields:
  - field_id: age
    datatable_id: SALARIES
    view_id: VW_PORTEFEUILLE_RETRAITE
    sql_expr: age

  - field_id: encours
    datatable_id: CONTRATS_RETRAITE
    view_id: VW_PORTEFEUILLE_RETRAITE
    sql_expr: encours
```

`datatable_id` preserves the physical origin of each field. `view_id` names the
curated projection through which the field may be selected in V2.

### `views.yml`

```yaml
views:
  - view_id: VW_PORTEFEUILLE_RETRAITE
    status: VALIDATED
    source_tables: [SALARIES, CONTRATS_RETRAITE]
    owner: validation_modeles
    validated_at: 2026-07-30
```

### V2 controls

1. The selection is non-empty.
2. Every field exists and duplicate field IDs are removed with a warning.
3. Every selected field references the same `view_id`.
4. The view exists in `views.yml`.
5. Its status is exactly `VALIDATED`.
6. Every selected field's `datatable_id` is covered by `source_tables`.
7. `view_id` matches `^[A-Z0-9_]+$`.
8. With `--execute`, the database object must exist as a real SQLite `VIEW`.

The generated query remains a simple projection:

```sql
SELECT age, encours
FROM VW_PORTEFEUILLE_RETRAITE;
```

V2 never generates a `JOIN`. The manifest records the SHA-256 of the stored SQL
view definition as well as the SHA-256 of `extract.csv`.

### V2 errors

| Code | Meaning |
|---|---|
| `COMMON_VIEW_REQUIRED` | Selected fields do not share one view |
| `VIEW_NOT_FOUND` | `view_id` is absent from `views.yml` |
| `VIEW_NOT_VALIDATED` | The catalogue status is not `VALIDATED` |
| `SOURCE_NOT_IN_VIEW` | A field's source table is outside the view perimeter |
| `VIEW_NOT_FOUND_IN_DATABASE` | Execution target is not a real SQLite view |

### Command

```text
python -m metaquery.cli <selection.yml> --fields <fields.yml> \
  --version V2 --views <views.yml> [--execute --db <database.db>]
```

## Future Version

### V3 — Explicit join mapping
- User provides join definitions with keys
- Cardinality validation (1:1, 1:N, N:M)
- Row explosion detection
- Additional controls on referential integrity

---

## Validation Logic Summary
```
1. Load fields.yml
2. Load selection.yml
3. Check non-empty selection
4. Check all fields exist
5. Auto-deduplicate (with warning)
6. Check single-source constraint ⚠️ CRITICAL
7. If all pass → generate SQL + audit.json + explain.txt
8. If any fail → error message + audit.json with BLOCK decision
```

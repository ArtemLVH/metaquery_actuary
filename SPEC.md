# MetaQuery V1 Specification

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

### Timestamps
- All timestamps in ISO 8601 UTC format
- Example: `2026-01-14T10:30:00Z`
- Generated at validation time, not at selection file creation

### YAML Parsing
- Use safe YAML loader (no arbitrary code execution)
- Clear error messages for malformed YAML
- Report line numbers for syntax errors

---

## Future Versions (V2/V3)

### V2 — Pre-validated views
- Multi-source allowed via explicit view definitions
- View metadata includes join logic and validation status
- Additional field: `view_id` in fields.yml

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

---

**End of Specification**
```

---

## **Commit message**
```
docs: add complete V1 technical specification

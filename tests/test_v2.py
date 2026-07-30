from __future__ import annotations

import sqlite3

import pytest

from metaquery.builder import build_sql_v2
from metaquery.executor import execute_sql, inspect_sqlite_view
from metaquery.loader import Field, View, load_views
from metaquery.validator import validate_v1, validate_v2

VIEW_ID = "VW_PORTEFEUILLE_RETRAITE"


def _fields():
    return {
        "id_salarie": Field("id_salarie", "SALARIES", "id_salarie", view_id=VIEW_ID),
        "age": Field("age", "SALARIES", "age", view_id=VIEW_ID),
        "produit": Field("produit", "CONTRATS_RETRAITE", "produit", view_id=VIEW_ID),
        "encours": Field("encours", "CONTRATS_RETRAITE", "encours", view_id=VIEW_ID),
    }


def _views(status: str = "VALIDATED"):
    return {
        VIEW_ID: View(
            view_id=VIEW_ID,
            status=status,
            source_tables=("SALARIES", "CONTRATS_RETRAITE"),
        )
    }


def _database(path, *, create_view: bool = True):
    con = sqlite3.connect(path)
    try:
        con.executescript(
            """
            CREATE TABLE SALARIES (
                id_salarie TEXT PRIMARY KEY,
                age INTEGER NOT NULL
            );
            CREATE TABLE CONTRATS_RETRAITE (
                id_salarie TEXT PRIMARY KEY,
                produit TEXT NOT NULL,
                encours REAL NOT NULL
            );
            INSERT INTO SALARIES VALUES ('S1', 51);
            INSERT INTO CONTRATS_RETRAITE VALUES ('S1', 'PERO', 75000.0);
            """
        )
        if create_view:
            con.execute(
                """
                CREATE VIEW VW_PORTEFEUILLE_RETRAITE AS
                SELECT s.id_salarie, s.age, c.produit, c.encours
                FROM SALARIES AS s
                JOIN CONTRATS_RETRAITE AS c ON c.id_salarie = s.id_salarie
                """
            )
        else:
            con.execute(
                """
                CREATE TABLE VW_PORTEFEUILLE_RETRAITE (
                    id_salarie TEXT, age INTEGER, produit TEXT, encours REAL
                )
                """
            )
        con.commit()
    finally:
        con.close()


def test_v2_allows_two_sources_through_one_validated_view():
    selected, audit = validate_v2(_fields(), ["id_salarie", "age", "produit"], _views())
    assert selected == ["id_salarie", "age", "produit"]
    assert audit.decision == "ALLOW"
    assert audit.version == "V2"
    assert audit.source == VIEW_ID


def test_v1_still_blocks_the_same_multisource_selection():
    _, audit = validate_v1(_fields(), ["id_salarie", "produit"])
    assert audit.decision == "BLOCK"
    assert audit.error["code"] == "MULTI_SOURCE_NOT_ALLOWED"


def test_v2_blocks_a_view_that_is_not_validated():
    _, audit = validate_v2(_fields(), ["id_salarie", "produit"], _views("DRAFT"))
    assert audit.decision == "BLOCK"
    assert audit.error["code"] == "VIEW_NOT_VALIDATED"


def test_v2_requires_one_common_view():
    fields = _fields()
    fields["produit"] = Field(
        "produit", "CONTRATS_RETRAITE", "produit", view_id="VW_AUTRE"
    )
    _, audit = validate_v2(fields, ["id_salarie", "produit"], _views())
    assert audit.decision == "BLOCK"
    assert audit.error["code"] == "COMMON_VIEW_REQUIRED"


def test_v2_checks_that_the_view_covers_every_source():
    views = {
        VIEW_ID: View(VIEW_ID, "VALIDATED", ("SALARIES",)),
    }
    _, audit = validate_v2(_fields(), ["id_salarie", "produit"], views)
    assert audit.decision == "BLOCK"
    assert audit.error["code"] == "SOURCE_NOT_IN_VIEW"


def test_v2_sql_reads_only_the_curated_view():
    selected, audit = validate_v2(_fields(), ["id_salarie", "produit"], _views())
    sql = build_sql_v2(audit.source, selected, _fields())
    assert f"FROM {VIEW_ID};" in sql
    assert " JOIN " not in sql


def test_execution_accepts_a_real_sqlite_view(tmp_path):
    db = tmp_path / "v2.db"
    _database(db)
    view_hash = inspect_sqlite_view(db, VIEW_ID)
    df = execute_sql(db, f"SELECT id_salarie, produit FROM {VIEW_ID};")
    assert len(view_hash) == 64
    assert df.to_dict("records") == [{"id_salarie": "S1", "produit": "PERO"}]


def test_execution_rejects_a_table_disguised_as_a_view(tmp_path):
    db = tmp_path / "fake.db"
    _database(db, create_view=False)
    with pytest.raises(ValueError, match="VIEW_NOT_FOUND_IN_DATABASE"):
        inspect_sqlite_view(db, VIEW_ID)


def test_views_catalogue_is_loaded(tmp_path):
    path = tmp_path / "views.yml"
    path.write_text(
        """
views:
  - view_id: VW_TEST
    status: validated
    source_tables: [TABLE_A, TABLE_B]
    validated_at: 2026-07-30
""".lstrip(),
        encoding="utf-8",
    )
    views = load_views(path)
    assert views["VW_TEST"].status == "VALIDATED"
    assert views["VW_TEST"].source_tables == ("TABLE_A", "TABLE_B")

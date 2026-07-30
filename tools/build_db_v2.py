"""Build a small multi-source SQLite demo with one curated retirement view."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("portefeuille_v2.db")
con = sqlite3.connect(db_path)
try:
    con.executescript(
        """
        DROP VIEW IF EXISTS VW_PORTEFEUILLE_RETRAITE;
        DROP TABLE IF EXISTS SALARIES;
        DROP TABLE IF EXISTS CONTRATS_RETRAITE;

        CREATE TABLE SALARIES (
            id_salarie TEXT PRIMARY KEY,
            age INTEGER NOT NULL,
            categorie TEXT NOT NULL,
            salaire REAL NOT NULL
        );

        CREATE TABLE CONTRATS_RETRAITE (
            id_salarie TEXT PRIMARY KEY,
            produit TEXT NOT NULL,
            encours REAL NOT NULL,
            age_liquidation INTEGER NOT NULL,
            FOREIGN KEY (id_salarie) REFERENCES SALARIES(id_salarie)
        );
        """
    )
    con.executemany(
        "INSERT INTO SALARIES VALUES (?, ?, ?, ?)",
        [
            ("SAL0001", 46, "Cadre", 72000.0),
            ("SAL0002", 53, "Non-cadre", 46500.0),
            ("SAL0003", 59, "Cadre", 88500.0),
        ],
    )
    con.executemany(
        "INSERT INTO CONTRATS_RETRAITE VALUES (?, ?, ?, ?)",
        [
            ("SAL0001", "PERO", 84000.0, 64),
            ("SAL0002", "PERECO", 37000.0, 63),
            ("SAL0003", "PERO", 142000.0, 65),
        ],
    )
    con.execute(
        """
        CREATE VIEW VW_PORTEFEUILLE_RETRAITE AS
        SELECT
            s.id_salarie,
            s.age,
            s.categorie,
            s.salaire,
            c.produit,
            c.encours,
            c.age_liquidation
        FROM SALARIES AS s
        INNER JOIN CONTRATS_RETRAITE AS c
            ON c.id_salarie = s.id_salarie
        """
    )
    con.commit()
finally:
    con.close()

print(f"{db_path}: 2 tables sources + vue validee VW_PORTEFEUILLE_RETRAITE")

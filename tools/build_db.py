"""Charge un CSV dans une base SQLite (table PORTEFEUILLE_EPARGNE)."""
import sqlite3
import sys

import pandas as pd

csv = sys.argv[1] if len(sys.argv) > 1 else "data_rachats.csv"
db  = sys.argv[2] if len(sys.argv) > 2 else "portefeuille.db"
df = pd.read_csv(csv)
con = sqlite3.connect(db)
df.to_sql("PORTEFEUILLE_EPARGNE", con, if_exists="replace", index=False)
con.close()
print(f"{db} : table PORTEFEUILLE_EPARGNE, {len(df)} lignes, {len(df.columns)} colonnes")

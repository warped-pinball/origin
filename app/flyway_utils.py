from __future__ import annotations

import re
from pathlib import Path
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "flyway" / "sql"


def _translate_sql(sql: str) -> str:
    """Translate Postgres-specific SQL syntax to SQLite."""
    replacements = {
        r"SERIAL PRIMARY KEY": "INTEGER PRIMARY KEY AUTOINCREMENT",
        r"SERIAL": "INTEGER",
        r"TIMESTAMPTZ": "TIMESTAMP",
        r"NOW\(\)": "CURRENT_TIMESTAMP",
    }
    for pattern, repl in replacements.items():
        sql = re.sub(pattern, repl, sql, flags=re.IGNORECASE)
    return sql


def apply_migrations(engine: Engine) -> None:
    """Apply all Flyway SQL migration scripts to the provided engine."""
    for path in sorted(MIGRATIONS_DIR.glob("V*__*.sql")):
        sql = _translate_sql(path.read_text())
        with engine.begin() as conn:
            conn.connection.executescript(sql)

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from app.flyway_utils import apply_migrations  # noqa: E402

DOC_PATH = ROOT / "docs" / "DB_SCHEMA.md"


@contextmanager
def _init_temp_db() -> Engine:
    """Yield an engine for a temporary database with migrations applied."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "schema.db"
        engine = create_engine(f"sqlite:///{db_path}")
        apply_migrations(engine)
        yield engine


def generate_schema_md() -> str:
    """Generate markdown description of the current database schema."""
    with _init_temp_db() as engine:
        insp = inspect(engine)
        tables = sorted(
            t for t in insp.get_table_names() if not t.startswith("sqlite_")
        )
        lines: List[str] = ["# Database Schema", ""]
        for table in tables:
            lines.append(f"## {table}")
            lines.append("")
            lines.append(
                "| Column | Type | Primary Key | Nullable | Default | Unique |"
            )
            lines.append("| --- | --- | --- | --- | --- | --- |")
            pk_cols = set(insp.get_pk_constraint(table).get("constrained_columns", []))
            unique_cols = set()
            for idx in insp.get_indexes(table):
                if idx.get("unique"):
                    unique_cols.update(idx.get("column_names", []))
            for uc in insp.get_unique_constraints(table):
                unique_cols.update(uc.get("column_names", []))
            for col in insp.get_columns(table):
                name = col["name"]
                col_type = str(col["type"])
                pk = name in pk_cols or bool(col.get("primary_key"))
                nullable = False if pk else col.get("nullable")
                default = col.get("default", col.get("server_default")) or ""
                unique = name in unique_cols
                lines.append(
                    f"| {name} | {col_type} | {pk} | {nullable} | {default} | {unique} |"
                )
            lines.append("")
        return "\n".join(lines)


def main() -> None:
    content = generate_schema_md()
    DOC_PATH.write_text(content + "\n")
    print(f"Schema documentation written to {DOC_PATH}")


if __name__ == "__main__":
    main()

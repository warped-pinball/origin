from __future__ import annotations
import os
import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from contextlib import contextmanager
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

# Ensure project root on sys.path for "app" imports when run as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

DOC_PATH = Path(__file__).resolve().parent.parent / "docs" / "DB_SCHEMA.md"


@contextmanager
def _init_temp_db() -> Engine:
    """Yield an engine for a temporary database with migrations applied."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "schema.db"
        old_url = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
            import app.database as db  # type: ignore
            importlib.reload(db)
            # Ensure models are loaded against this Base
            if "app.models" in sys.modules:
                models = sys.modules["app.models"]
                importlib.reload(models)  # type: ignore[arg-type]
            else:
                import app.models as models  # type: ignore
            db.init_db()
            yield db.engine
        finally:
            if old_url is not None:
                os.environ["DATABASE_URL"] = old_url
            else:
                os.environ.pop("DATABASE_URL", None)
            # Restore database module using original environment
            importlib.reload(db)


def generate_schema_md() -> str:
    """Generate markdown description of the current database schema."""
    with _init_temp_db() as engine:
        insp = inspect(engine)
        tables = sorted(t for t in insp.get_table_names() if not t.startswith("sqlite_"))
        lines: List[str] = ["# Database Schema", ""]
        for table in tables:
            lines.append(f"## {table}")
            lines.append("")
            lines.append("| Column | Type | Primary Key | Nullable | Default | Unique |")
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
                nullable = col.get("nullable")
                default = col.get("default", col.get("server_default")) or ""
                unique = name in unique_cols
                lines.append(
                    f"| {name} | {col_type} | {pk} | {nullable} | {default} | {unique} |")
            lines.append("")
        return "\n".join(lines)


def main() -> None:
    content = generate_schema_md()
    DOC_PATH.write_text(content + "\n")
    print(f"Schema documentation written to {DOC_PATH}")


if __name__ == "__main__":
    main()

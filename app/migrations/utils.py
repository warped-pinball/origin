from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateTable, CreateColumn


def table_exists(engine, name: str) -> bool:
    return name in inspect(engine).get_table_names()


def column_exists(engine, table_name: str, column_name: str) -> bool:
    if not table_exists(engine, table_name):
        return False
    insp = inspect(engine)
    return column_name in {c['name'] for c in insp.get_columns(table_name)}


def ensure_table(engine, table) -> None:
    """Create table if it does not exist and add any missing columns."""
    insp = inspect(engine)
    if table.name not in insp.get_table_names():
        with engine.begin() as conn:
            conn.execute(CreateTable(table))
        return
    existing = {c['name'] for c in insp.get_columns(table.name)}
    with engine.begin() as conn:
        for col in table.columns:
            if col.name not in existing:
                sql = f"ALTER TABLE {table.name} ADD COLUMN {CreateColumn(col).compile(dialect=engine.dialect)}"
                conn.execute(text(sql))


def add_column(engine, table_name: str, column) -> None:
    """Add column to table if it does not already exist.

    This function is resilient to concurrent attempts to add the same column
    by swallowing duplicate-column errors emitted by the database.
    """
    if column_exists(engine, table_name, column.name):
        return
    sql = f"ALTER TABLE {table_name} ADD COLUMN {CreateColumn(column).compile(dialect=engine.dialect)}"
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
    except SQLAlchemyError as e:  # pragma: no cover - error path tested separately
        msg = str(getattr(e, "orig", e)).lower()
        if "duplicate column" in msg or "already exists" in msg:
            return
        raise


def drop_column(engine, table_name: str, column_name: str) -> None:
    if column_exists(engine, table_name, column_name):
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))


def rename_column(engine, table_name: str, old_name: str, new_name: str) -> None:
    if column_exists(engine, table_name, old_name) and not column_exists(engine, table_name, new_name):
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}"))

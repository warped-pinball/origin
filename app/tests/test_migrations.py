import os
import importlib
from sqlalchemy import (
    Column,
    Integer,
    String,
    inspect,
    create_engine,
    MetaData,
    Table,
)
from app.migrations import utils


def test_run_all_migrations(tmp_path):
    db_file = tmp_path / "migrate.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    if db_file.exists():
        db_file.unlink()
    import app.database as db

    importlib.reload(db)

    db.run_migrations()
    db.Base.metadata.create_all(bind=db.engine)

    assert db.get_db_version() == db.EXPECTED_DB_VERSION == 1

    insp = inspect(db.engine)
    tables = set(insp.get_table_names())
    for table in [
        "users",
        "locations",
        "machines",
        "machine_claims",
        "machine_challenges",
        "scores",
        "qr_codes",
    ]:
        assert table in tables

    user_cols = {c["name"] for c in insp.get_columns("users")}
    for col in [
        "email",
        "hashed_password",
        "screen_name",
        "first_name",
        "last_name",
        "name",
        "initials",
        "profile_picture",
        "is_verified",
        "verification_token",
        "reset_token",
    ]:
        assert col in user_cols

    qr_cols = {c["name"] for c in insp.get_columns("qr_codes")}
    for col in [
        "url",
        "created_at",
        "generated_at",
        "nfc_link",
        "user_id",
        "machine_id",
    ]:
        assert col in qr_cols


def test_add_column_duplicate_is_ignored(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    Table(
        "users",
        meta,
        Column("id", Integer, primary_key=True),
        Column("initials", String(3)),
    )
    meta.create_all(engine)

    monkeypatch.setattr(utils, "column_exists", lambda *args, **kwargs: False)
    utils.add_column(engine, "users", Column("initials", String(3)))

    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("users")]
    assert cols.count("initials") == 1

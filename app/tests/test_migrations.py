from sqlalchemy import create_engine, inspect

from app.flyway_utils import apply_migrations


def test_apply_migrations_creates_expected_schema(tmp_path):
    db_file = tmp_path / "migrate.db"
    engine = create_engine(f"sqlite:///{db_file}")
    apply_migrations(engine)

    insp = inspect(engine)
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

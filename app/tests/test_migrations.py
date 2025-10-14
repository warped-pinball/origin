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
        "machine_challenges",
        "scores",
        "qr_codes",
        "machine_game_states",
    ]:
        assert table in tables

    # ensure legacy tables were removed
    for table in ["machines_old", "scores_old", "qr_codes_old"]:
        assert table not in tables

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

    machine_cols = {c["name"] for c in insp.get_columns("machines")}
    for col in [
        "id",
        "game_title",
        "shared_secret",
        "user_id",
        "location_id",
        "claim_code",
    ]:
        assert col in machine_cols

    state_cols = {c["name"] for c in insp.get_columns("machine_game_states")}
    for col in [
        "id",
        "machine_id",
        "created_at",
        "time_ms",
        "ball_in_play",
        "scores",
        "player_up",
        "players_total",
        "game_active",
    ]:
        assert col in state_cols

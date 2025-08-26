from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    func,
)
from app.migrations.utils import ensure_table


def upgrade(engine):
    meta = MetaData()

    users = Table(
        "users",
        meta,
        Column("id", Integer, primary_key=True),
        Column("email", String(255), unique=True, nullable=False),
        Column("hashed_password", String, nullable=False),
        Column("screen_name", String, unique=True),
        Column("first_name", String),
        Column("last_name", String),
        Column("name", String),
        Column("initials", String(3)),
        Column("profile_picture", String),
        Column("is_verified", Boolean, server_default="0"),
        Column("verification_token", String, unique=True),
        Column("reset_token", String, unique=True),
    )
    ensure_table(engine, users)

    locations = Table(
        "locations",
        meta,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("name", String, nullable=False),
        Column("address", String),
        Column("website", String),
        Column("hours", String),
    )
    ensure_table(engine, locations)

    machines = Table(
        "machines",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", String, unique=True, nullable=False),
        Column("shared_secret", String, nullable=False),
        Column("user_id", Integer, ForeignKey("users.id")),
        Column("location_id", Integer, ForeignKey("locations.id")),
    )
    ensure_table(engine, machines)

    machine_claims = Table(
        "machine_claims",
        meta,
        Column("machine_id", String, primary_key=True),
        Column("claim_code", String, unique=True, nullable=False),
        Column("game_title", String, nullable=False),
        Column("claimed", Boolean, server_default="0", nullable=False),
        Column("user_id", Integer, ForeignKey("users.id")),
    )
    ensure_table(engine, machine_claims)

    machine_challenges = Table(
        "machine_challenges",
        meta,
        Column("challenge", String, primary_key=True),
        Column("machine_id", String, nullable=False),
        Column(
            "issued_at",
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    ensure_table(engine, machine_challenges)

    scores = Table(
        "scores",
        meta,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("users.id")),
        Column("machine_id", Integer, ForeignKey("machines.id")),
        Column("game", String),
        Column("value", Integer),
        Column(
            "created_at",
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    ensure_table(engine, scores)

    qr_codes = Table(
        "qr_codes",
        meta,
        Column("id", Integer, primary_key=True),
        Column("url", String, unique=True, nullable=False),
        Column(
            "created_at",
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
        Column("generated_at", DateTime(timezone=True)),
        Column("nfc_link", String),
        Column("user_id", Integer, ForeignKey("users.id")),
        Column("machine_id", Integer, ForeignKey("machines.id")),
    )
    ensure_table(engine, qr_codes)

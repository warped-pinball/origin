import os
import importlib
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, inspect, text
from sqlalchemy.orm import declarative_base


def create_v0_schema(engine):
    BaseV0 = declarative_base()

    class User(BaseV0):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True, index=True)
        email = Column(String, unique=True, index=True, nullable=False)
        hashed_password = Column(String, nullable=False)

    class Machine(BaseV0):
        __tablename__ = 'machines'
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String, unique=True, index=True)
        secret = Column(String, nullable=False)

    class Score(BaseV0):
        __tablename__ = 'scores'
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, ForeignKey('users.id'))
        machine_id = Column(Integer, ForeignKey('machines.id'))
        game = Column(String, index=True)
        value = Column(Integer)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

    BaseV0.metadata.create_all(bind=engine)


def test_run_all_migrations(tmp_path):
    db_file = tmp_path / "migrate.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    if db_file.exists():
        db_file.unlink()
    import app.database as db
    importlib.reload(db)

    # Create initial schema (version 0)
    create_v0_schema(db.engine)
    db.run_migrations()
    # After migrating, ensure any new tables exist
    db.Base.metadata.create_all(bind=db.engine)

    assert db.get_db_version() == db.EXPECTED_DB_VERSION

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("users")}
    for col in ["screen_name", "first_name", "last_name", "name", "initials", "profile_picture"]:
        assert col in cols
    if db.engine.dialect.name != 'sqlite':
        # verify users.id column autoincrements via sequence
        with db.engine.connect() as conn:
            res = conn.execute(
                text(
                    "SELECT column_default FROM information_schema.columns "
                    "WHERE table_name='users' AND column_name='id'"
                )
            )
            default = res.scalar()
            assert default and 'nextval' in default

    assert "machine_claims" in insp.get_table_names()


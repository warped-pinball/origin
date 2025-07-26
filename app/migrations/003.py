from sqlalchemy import text
from app.migrations.utils import table_exists


def upgrade(engine):
    if engine.dialect.name == 'sqlite':
        return
    if not table_exists(engine, 'users'):
        return
    with engine.begin() as conn:
        default_res = conn.execute(text(
            """
            SELECT column_default
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='id'
            """
        ))
        default = default_res.scalar()
        if not default or 'nextval' not in str(default):
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS users_id_seq"))
            conn.execute(text(
                "SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 0) + 1, false)"
            ))
            conn.execute(text(
                "ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq')"
            ))



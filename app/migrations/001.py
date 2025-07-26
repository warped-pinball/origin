from sqlalchemy import MetaData, Table, Column, Integer, String
from app.migrations.utils import ensure_table, add_column


def upgrade(engine):
    meta = MetaData()
    users = Table(
        'users',
        meta,
        Column('id', Integer, primary_key=True),
        Column('email', String, unique=True, nullable=False),
        Column('hashed_password', String, nullable=False),
    )
    ensure_table(engine, users)
    add_column(engine, 'users', Column('screen_name', String))


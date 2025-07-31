from sqlalchemy import MetaData, Table, Column, String, Integer, Boolean, ForeignKey
from app.migrations.utils import ensure_table


def upgrade(engine):
    meta = MetaData()
    # reflect users table so foreign key can be created
    Table('users', meta, autoload_with=engine)
    machine_claims = Table(
        'machine_claims',
        meta,
        Column('machine_id', String, primary_key=True),
        Column('claim_code', String, unique=True, index=True),
        Column('shared_secret', String, nullable=False),
        Column('claimed', Boolean, nullable=False, default=False),
        Column('user_id', Integer, ForeignKey('users.id')),
    )
    ensure_table(engine, machine_claims)

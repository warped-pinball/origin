from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, ForeignKey, func
from app.migrations.utils import ensure_table


def upgrade(engine):
    meta = MetaData()
    Table('users', meta, Column('id', Integer, primary_key=True))
    Table('machines', meta, Column('id', Integer, primary_key=True))
    qr_codes = Table(
        'qr_codes',
        meta,
        Column('id', Integer, primary_key=True),
        Column('url', String, unique=True, nullable=False),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('generated_at', DateTime(timezone=True)),
        Column('nfc_link', String),
        Column('user_id', Integer, ForeignKey('users.id')),
        Column('machine_id', Integer, ForeignKey('machines.id')),
    )
    ensure_table(engine, qr_codes)

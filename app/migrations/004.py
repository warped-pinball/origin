from sqlalchemy import Column, Boolean, String
from app.migrations.utils import add_column, table_exists


def upgrade(engine):
    if not table_exists(engine, 'users'):
        return
    add_column(engine, 'users', Column('is_verified', Boolean, server_default='0'))
    add_column(engine, 'users', Column('verification_token', String(255)))
    add_column(engine, 'users', Column('reset_token', String(255)))

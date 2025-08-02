from sqlalchemy import Column, String
from app.migrations.utils import table_exists, column_exists, rename_column, add_column


def upgrade(engine):
    if not table_exists(engine, 'users'):
        return
    if column_exists(engine, 'users', 'email'):
        return
    if column_exists(engine, 'users', 'phone'):
        rename_column(engine, 'users', 'phone', 'email')
    else:
        add_column(engine, 'users', Column('email', String, unique=True, nullable=False))


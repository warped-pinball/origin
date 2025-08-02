from sqlalchemy import Column, String
from app.migrations.utils import table_exists, column_exists, rename_column, add_column

def upgrade(engine):
    if not table_exists(engine, 'users'):
        return
    if column_exists(engine, 'users', 'phone'):
        return
    if column_exists(engine, 'users', 'email'):
        rename_column(engine, 'users', 'email', 'phone')
    else:
        add_column(engine, 'users', Column('phone', String, unique=True, nullable=False))

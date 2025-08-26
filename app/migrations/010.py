from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey
from app.migrations.utils import ensure_table, add_column, table_exists, drop_column


def upgrade(engine):
    meta = MetaData()
    
    # Add shared_secret column to machines table
    if table_exists(engine, 'machines'):
        add_column(engine, 'machines', Column('shared_secret', String))
    
    # Remove columns from machine_claims table
    if table_exists(engine, 'machine_claims'):
        drop_column(engine, 'machine_claims', 'user_id')
        drop_column(engine, 'machine_claims', 'claimed')
        drop_column(engine, 'machine_claims', 'game_title')
        

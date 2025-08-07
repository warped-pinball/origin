from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey
from app.migrations.utils import ensure_table, add_column, table_exists


def upgrade(engine):
    meta = MetaData()
    Table('users', meta, Column('id', Integer, primary_key=True))
    locations = Table(
        'locations',
        meta,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        Column('name', String, nullable=False),
        Column('address', String),
        Column('website', String),
        Column('hours', String),
    )
    ensure_table(engine, locations)
    if table_exists(engine, 'machines'):
        add_column(engine, 'machines', Column('user_id', Integer, ForeignKey('users.id')))
        add_column(engine, 'machines', Column('location_id', Integer, ForeignKey('locations.id')))

from sqlalchemy import Column, String
from app.migrations.utils import add_column


def upgrade(engine):
    add_column(engine, 'users', Column('first_name', String))
    add_column(engine, 'users', Column('last_name', String))
    add_column(engine, 'users', Column('name', String))
    add_column(engine, 'users', Column('initials', String(3)))
    add_column(engine, 'users', Column('profile_picture', String))


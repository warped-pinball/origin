from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    screen_name = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    name = Column(String)
    initials = Column(String(3))
    profile_picture = Column(String)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, unique=True, index=True)
    reset_token = Column(String, unique=True, index=True)
    scores = relationship('Score', back_populates='user')

class Machine(Base):
    __tablename__ = 'machines'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    secret = Column(String, nullable=False)
    scores = relationship('Score', back_populates='machine')

class Score(Base):
    __tablename__ = 'scores'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    machine_id = Column(Integer, ForeignKey('machines.id'))
    game = Column(String, index=True)
    value = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User', back_populates='scores')
    machine = relationship('Machine', back_populates='scores')

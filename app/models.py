from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    ip_address = Column(String)
    last_seen = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    games = relationship("Game", back_populates="machine")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    initials = Column(String, index=True)
    screen_name = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone_number = Column(String)

    game_players = relationship("GamePlayer", back_populates="player")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    machine = relationship("Machine", back_populates="games")
    game_players = relationship("GamePlayer", back_populates="game")
    game_states = relationship("GameState", back_populates="game")


class GamePlayer(Base):
    __tablename__ = "game_players"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    player_number = Column(Integer)

    game = relationship("Game", back_populates="game_players")
    player = relationship("Player", back_populates="game_players")


class GameState(Base):
    __tablename__ = "game_states"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    seconds_elapsed = Column(Integer)
    ball = Column(Integer)
    player_up = Column(Integer)
    scores = Column(JSON)

    game = relationship("Game", back_populates="game_states")

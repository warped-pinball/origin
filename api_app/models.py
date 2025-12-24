from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import datetime

class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    uid = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=False)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    version = Column(String, nullable=True)
    version_checked_at = Column(DateTime(timezone=True), nullable=True)

    games = relationship("Game", back_populates="machine")

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    initials = Column(String(3), nullable=False, unique=True)
    screen_name = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)

    game_players = relationship("GamePlayer", back_populates="player")

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    admin_password = Column(String, nullable=True)

    machine = relationship("Machine", back_populates="games")
    game_players = relationship("GamePlayer", back_populates="game")
    game_states = relationship("GameState", back_populates="game")

class GamePlayer(Base):
    __tablename__ = "game_players"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    player_number = Column(Integer, nullable=False)

    game = relationship("Game", back_populates="game_players")
    player = relationship("Player", back_populates="game_players")

class GameState(Base):
    __tablename__ = "game_states"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    seconds_elapsed = Column(Integer, nullable=False)
    ball = Column(Integer, nullable=False)
    player_up = Column(Integer, nullable=False)
    scores = Column(JSON, nullable=False)

    game = relationship("Game", back_populates="game_states")


class GameMode(Base):
    __tablename__ = "game_modes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    activation_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tournaments = relationship("Tournament", back_populates="game_mode")


class LeaderboardProfile(Base):
    __tablename__ = "leaderboard_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    sql_template = Column(Text, nullable=False)
    sort_direction = Column(String, nullable=False, default="desc")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tournaments = relationship("Tournament", back_populates="scoring_profile")


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    scoring_profile_id = Column(Integer, ForeignKey("leaderboard_profiles.id"), nullable=False)
    game_mode_id = Column(Integer, ForeignKey("game_modes.id"), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    display_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    scoring_profile = relationship("LeaderboardProfile", back_populates="tournaments")
    game_mode = relationship("GameMode", back_populates="tournaments")
    machines = relationship("TournamentMachine", back_populates="tournament", cascade="all, delete-orphan")
    players = relationship("TournamentPlayer", back_populates="tournament", cascade="all, delete-orphan")


class TournamentMachine(Base):
    __tablename__ = "tournament_machines"
    __table_args__ = (UniqueConstraint("tournament_id", "machine_id", name="uq_tournament_machine"),)

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)

    tournament = relationship("Tournament", back_populates="machines")
    machine = relationship("Machine")


class TournamentPlayer(Base):
    __tablename__ = "tournament_players"
    __table_args__ = (UniqueConstraint("tournament_id", "player_id", name="uq_tournament_player"),)

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)

    tournament = relationship("Tournament", back_populates="players")
    player = relationship("Player")

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    func,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"
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
    scores = relationship("Score", back_populates="user")
    locations = relationship("Location", back_populates="user")
    machines = relationship("Machine", back_populates="user")


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    address = Column(String)
    website = Column(String)
    hours = Column(String)

    user = relationship("User", back_populates="locations")
    machines = relationship("Machine", back_populates="location")


class Machine(Base):
    __tablename__ = "machines"
    id = Column(String, primary_key=True, index=True)
    game_title = Column(String, unique=False, index=True)
    shared_secret = Column(String, unique=True, nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    claim_code = Column(String, unique=True, index=True, nullable=True)
    user = relationship("User", back_populates="machines", foreign_keys=[user_id])
    location = relationship("Location", back_populates="machines")
    scores = relationship("Score", back_populates="machine")
    game_states = relationship(
        "MachineGameState",
        back_populates="machine",
        cascade="all, delete-orphan",
    )

class MachineChallenge(Base):
    __tablename__ = "machine_challenges"
    challenge = Column(String, primary_key=True, index=True)
    machine_id = Column(String, index=True, nullable=False)
    issued_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    machine_id = Column(String, ForeignKey("machines.id"))
    game = Column(String, index=True)
    value = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    duration_ms = Column(Integer, nullable=True)

    user = relationship("User", back_populates="scores")
    machine = relationship("Machine", back_populates="scores")


class MachineGameState(Base):
    __tablename__ = "machine_game_states"
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    time_ms = Column(Integer, nullable=False)
    ball_in_play = Column(Integer, nullable=False)
    scores = Column(JSON, nullable=False)
    player_up = Column(Integer, nullable=True)
    players_total = Column(Integer, nullable=True)
    game_active = Column(Boolean, nullable=True)

    machine = relationship("Machine", back_populates="game_states")


class QRCode(Base):
    __tablename__ = "qr_codes"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    generated_at = Column(DateTime(timezone=True))
    nfc_link = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    machine_id = Column(String, ForeignKey("machines.id"))

    user = relationship("User")
    machine = relationship("Machine")

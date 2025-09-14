from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from .database import Base
import uuid


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
    machines = relationship("Machine", back_populates="owner")


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
    game_title = Column(String, unique=True, index=True)
    shared_secret = Column(String, nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"))

    owner = relationship("User", back_populates="machines")
    location = relationship("Location", back_populates="machines")
    scores = relationship("Score", back_populates="machine")


class MachineClaim(Base):
    __tablename__ = "machine_claims"
    id = Column(
        String(36),
        primary_key=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid.uuid1()),
    )
    machine_id = Column(String, ForeignKey("machines.id"), index=True, nullable=False)
    claim_code = Column(String, unique=True, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


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

    user = relationship("User", back_populates="scores")
    machine = relationship("Machine", back_populates="scores")


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

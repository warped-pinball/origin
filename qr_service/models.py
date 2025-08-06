from sqlalchemy import Column, DateTime, Integer, String, func

try:  # pragma: no cover - fallback for running as a top-level module
    from .database import Base
except ImportError:  # pragma: no cover
    from database import Base


class QRCode(Base):
    __tablename__ = "qr_codes"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_at = Column(DateTime(timezone=True))
    nfc_link = Column(String)
    user_id = Column(Integer)
    machine_id = Column(Integer)

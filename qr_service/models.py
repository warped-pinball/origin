from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from .database import Base


class QRCode(Base):
    __tablename__ = "qr_codes"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_at = Column(DateTime(timezone=True))
    nfc_link = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    machine_id = Column(Integer, ForeignKey("machines.id"))

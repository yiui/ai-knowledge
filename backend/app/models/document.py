from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from datetime import datetime
from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(
        String, 
        nullable=False,
        unique=True, 
        index=True
    )
    path = Column(String, nullable=False)
    size = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
import json
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pubkey: Mapped[str] = mapped_column(String(44), nullable=False)
    premium_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=True
    )

    def __repr__(self):
        return f"<User(id={self.id}, pubkey={self.pubkey})>"


class UserEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, User):
            return {
                "id": obj.id,
                "pubkey": obj.pubkey,
                "premium_end": obj.premium_end.isoformat() if obj.premium_end else None,
            }
        return super().default(obj)

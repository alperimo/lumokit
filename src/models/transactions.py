import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pubkey: Mapped[str] = mapped_column(String, nullable=False)
    tx_hash: Mapped[str] = mapped_column(String, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Transaction(id={self.id}, pubkey={self.pubkey}, tx_hash={self.tx_hash}, success={self.success})>"


class TransactionEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Transaction):
            return {
                "id": obj.id,
                "pubkey": obj.pubkey,
                "tx_hash": obj.tx_hash,
                "success": obj.success,
                "time": obj.time.isoformat() if obj.time else None,
            }
        return super().default(obj)

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LoginLogs(Base):
    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pubkey: Mapped[str] = mapped_column(String, nullable=False)
    time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<LoginLogs(id={self.id}, pubkey={self.pubkey})>"


class LoginLogsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, LoginLogs):
            return {
                "id": obj.id,
                "pubkey": obj.pubkey,
                "time": obj.time.isoformat() if obj.time else None,
            }
        return super().default(obj)

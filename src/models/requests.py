import json
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Requests(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pubkey: Mapped[str] = mapped_column(String, nullable=False)
    conversation_key: Mapped[str] = mapped_column(String, nullable=False)
    input_params: Mapped[dict] = mapped_column(JSON, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    response: Mapped[str] = mapped_column(Text, nullable=True)
    verbose: Mapped[str] = mapped_column(Text, nullable=True)
    liked: Mapped[bool] = mapped_column(Boolean, nullable=True)
    input_token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    output_token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    total_token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Requests(id={self.id}, pubkey={self.pubkey}, conversation_key={self.conversation_key})>"


class RequestsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Requests):
            return {
                "id": obj.id,
                "pubkey": obj.pubkey,
                "conversation_key": obj.conversation_key,
                "input_params": obj.input_params,
                "message": obj.message,
                "success": obj.success,
                "response": obj.response,
                "verbose": obj.verbose,
                "liked": obj.liked,
                "input_token_count": obj.input_token_count,
                "output_token_count": obj.output_token_count,
                "total_token_count": obj.total_token_count,
                "time": obj.time.isoformat() if obj.time else None,
            }
        return super().default(obj)

"""Chat session and message models."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.feedback import Feedback, UnansweredQuestion
    from app.models.user import User

import uuid

from sqlalchemy import Boolean, CheckConstraint, Float, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey

from app.models.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChatSession user={self.user_id} title={self.title!r}>"


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="ck_chat_messages_role"),
        Index("idx_msgs_session", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[object] = mapped_column(
        JSONB, nullable=False, server_default="'[]'"
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    was_refused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="FALSE"
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    feedbacks: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="message"
    )
    unanswered: Mapped[list["UnansweredQuestion"]] = relationship(
        "UnansweredQuestion", back_populates="message"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage role={self.role!r} session={self.session_id}>"

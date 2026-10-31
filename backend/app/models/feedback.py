"""Feedback and UnansweredQuestion models."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat import ChatMessage
    from app.models.user import User


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("rating IN (-1, 1)", name="ck_feedback_rating"),
        UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),
        Index("idx_feedback_message", "message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # relationships
    message: Mapped[ChatMessage] = relationship("ChatMessage", back_populates="feedbacks")
    user: Mapped[User] = relationship("User", back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<Feedback message={self.message_id} rating={self.rating}>"


class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"
    __table_args__ = (
        CheckConstraint(
            "reason IN ('low_confidence','no_permitted_docs','llm_refused')",
            name="ck_unanswered_reason",
        ),
        CheckConstraint(
            "status IN ('open','resolved','ignored')", name="ck_unanswered_status"
        ),
        Index(
            "idx_unanswered_status",
            "status",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    top_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="'open'")
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # relationships
    message: Mapped[ChatMessage | None] = relationship(
        "ChatMessage", back_populates="unanswered"
    )
    user: Mapped[User | None] = relationship(
        "User", foreign_keys=[user_id], overlaps="resolver"
    )
    resolver: Mapped[User | None] = relationship(
        "User", foreign_keys=[resolved_by], overlaps="user"
    )

    def __repr__(self) -> str:
        return f"<UnansweredQuestion reason={self.reason!r} status={self.status!r}>"

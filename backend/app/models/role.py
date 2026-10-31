"""Role model – RBAC seed table (employee=1, agent=2, admin=3)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)

    # relationships (back-populated by User)
    users: Mapped[list[User]] = relationship("User", back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.name!r} level={self.level}>"

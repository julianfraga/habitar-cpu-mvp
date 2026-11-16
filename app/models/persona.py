from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


if TYPE_CHECKING:
    from app.models.actividad import Docente
    from app.models.user import User



class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    usuario: Mapped["User | None"] = relationship(
        back_populates="persona", uselist=False, passive_deletes="all"
    )
    docente: Mapped["Docente | None"] = relationship(
        back_populates="persona", uselist=False, passive_deletes="all"
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    # @email.setter
    # def email(self, value: str | None) -> None:
    #     self.email = value.strip() if value else None
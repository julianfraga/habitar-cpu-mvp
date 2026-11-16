from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.actividad import Actividad
from app.models.enums import INSCRIPCION_ALTA
from app.models.user import User


class Inscripcion(Base):
    __tablename__ = "inscripciones"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('inscripto', 'baja')",
            name="ck_inscripciones_estado_valido",
        ),
        UniqueConstraint("actividad_id", "user_id", name="uq_enroll_actividad_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actividad_id: Mapped[int] = mapped_column(
        ForeignKey("actividades.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    estado: Mapped[str] = mapped_column(
        String(20),
        default=INSCRIPCION_ALTA,
        server_default=text(f"'{INSCRIPCION_ALTA.value}'"),
        index=True,
    )
    baja_penalizada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    reminded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actividad: Mapped["Actividad"] = relationship(back_populates="inscripciones")
    user: Mapped["User"] = relationship()

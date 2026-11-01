from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.actividad import Actividad
    from app.models.estudiante import Estudiante


class RespuestaEncuesta(Base):
    __tablename__ = "respuestas_encuesta"
    __table_args__ = (
        Index(
            "uq_respuesta_actividad_estudiante",
            "actividad_id",
            "estudiante_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actividad_id: Mapped[int] = mapped_column(
        ForeignKey("actividades.id", ondelete="CASCADE"), index=True
    )
    estudiante_id: Mapped[int] = mapped_column(
        ForeignKey("estudiantes.user_id", ondelete="CASCADE")
    )
    respuestas: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actividad: Mapped["Actividad"] = relationship(
        back_populates="respuestas_encuesta"
    )
    estudiante: Mapped["Estudiante"] = relationship(
        back_populates="respuestas_encuesta"
    )

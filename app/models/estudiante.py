from __future__ import annotations

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.carrera import Carrera
    from app.models.respuesta_encuesta import RespuestaEncuesta

class Estudiante(Base):
    __tablename__ = "estudiantes"
    __table_args__ = (
        CheckConstraint("creditos_acreditados >= 0", name="ck_estudiante_creditos_acreditados"),
        CheckConstraint("creditos_requeridos > 0", name="ck_estudiante_creditos_requeridos"),
        CheckConstraint("creditos_penalizacion >= 0", name="ck_estudiante_creditos_penalizacion"),
        CheckConstraint(
            "creditos_acreditados * 2 = CAST(creditos_acreditados * 2 AS INTEGER)",
            name="ck_estudiante_creditos_acreditados_medio",
        ),
        CheckConstraint(
            "creditos_requeridos * 2 = CAST(creditos_requeridos * 2 AS INTEGER)",
            name="ck_estudiante_creditos_requeridos_medio",
        ),
        CheckConstraint(
            "creditos_penalizacion * 2 = CAST(creditos_penalizacion * 2 AS INTEGER)",
            name="ck_estudiante_creditos_penalizacion_medio",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    carrera_id: Mapped[int | None] = mapped_column(
        ForeignKey("carreras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    creditos_acreditados: Mapped[Decimal] = mapped_column(
        Numeric(8, 1),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    creditos_requeridos: Mapped[Decimal] = mapped_column(
        Numeric(8, 1),
        nullable=False,
        default=Decimal("10"),
        server_default=text("10"),
    )
    creditos_penalizacion: Mapped[Decimal] = mapped_column(
        Numeric(8, 1),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )

    user: Mapped["User"] = relationship(back_populates="estudiante")
    carrera: Mapped["Carrera | None"] = relationship(back_populates="estudiantes")
    respuestas_encuesta: Mapped[list["RespuestaEncuesta"]] = relationship(
        back_populates="estudiante", passive_deletes="all"
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.user.nombre} {self.user.apellido}".strip()
    @property
    def email(self) -> str | None:
        return self.user.email if self.user else None

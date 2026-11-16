from sqlalchemy import Column, ForeignKey, Index, Table

from app.database import Base

actividad_carrera = Table(
    "actividad_carrera",
    Base.metadata,
    Column("actividad_id", ForeignKey("actividades.id", ondelete="CASCADE"), primary_key=True),
    Column("carrera_id", ForeignKey("carreras.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_actividad_carrera_carrera_id", "carrera_id"),
)

actividad_docente = Table(
    "actividad_docente",
    Base.metadata,
    Column(
        "actividad_id",
        ForeignKey("actividades.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "docente_id",
        ForeignKey("docentes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

"""Analytics service (E-10). Aggregates for the coordination/director dashboard."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Actividad,
    Asistencia,
    ESTADO_PUBLICADA,
    Estudiante,
    Inscripcion,
    INSCRIPCION_ALTA,
    RespuestaEncuesta,
    User,
)
from app.services.parsing import formatear_duracion


def overview(db: Session) -> dict:
    publicadas = db.query(Actividad).filter(Actividad.estado == ESTADO_PUBLICADA).count()
    inscripciones = db.query(Inscripcion).filter(Inscripcion.estado == INSCRIPCION_ALTA).count()
    asistencias = db.query(Asistencia).count()
    rate = round(asistencias / inscripciones * 100, 1) if inscripciones else 0.0
    return {
        "actividades_publicadas": publicadas,
        "inscripciones": inscripciones,
        "asistencias": asistencias,
        "asistencia_rate": rate,
    }


def top_actividades(db: Session, limit: int = 5) -> list[dict]:
    rows = (
        db.query(Actividad.titulo, func.count(Inscripcion.id).label("n"))
        .join(Inscripcion, Inscripcion.actividad_id == Actividad.id)
        .filter(Inscripcion.estado == INSCRIPCION_ALTA)
        .group_by(Actividad.id, Actividad.titulo)
        .order_by(func.count(Inscripcion.id).desc())
        .limit(limit)
        .all()
    )
    return [{"titulo": r[0], "inscriptos": int(r[1])} for r in rows]


def asistencia_per_actividad(db: Session) -> list[dict]:
    """Published actividades that have at least one enrollment (skip empty/draft ones)."""
    result = []
    actividades = (
        db.query(Actividad)
        .filter(Actividad.estado == ESTADO_PUBLICADA)
        .order_by(Actividad.fecha_inicio.desc())
        .all()
    )
    for a in actividades:
        insc = (
            db.query(Inscripcion)
            .filter(Inscripcion.actividad_id == a.id, Inscripcion.estado == INSCRIPCION_ALTA)
            .count()
        )
        if insc == 0:
            continue
        asis = db.query(Asistencia).filter(Asistencia.actividad_id == a.id).count()
        result.append(
            {
                "titulo": a.titulo,
                "inscriptos": insc,
                "asistencias": asis,
                "rate": round(asis / insc * 100, 1) if insc else 0.0,
            }
        )
    return result


def survey_averages(db: Session) -> list[dict]:
    rows = (
        db.query(
            Actividad.titulo,
            func.avg(RespuestaEncuesta.rating).label("avg"),
            func.count(RespuestaEncuesta.id).label("n"),
        )
        .join(RespuestaEncuesta, RespuestaEncuesta.actividad_id == Actividad.id)
        .group_by(Actividad.id, Actividad.titulo)
        .order_by(func.avg(RespuestaEncuesta.rating).desc())
        .all()
    )
    return [
        {"titulo": r[0], "promedio": round(float(r[1]), 2), "respuestas": int(r[2])}
        for r in rows
    ]


def actividad_detalle(db: Session, actividad: Actividad) -> dict:
    inscriptos = (
        db.query(Inscripcion)
        .filter(
            Inscripcion.actividad_id == actividad.id,
            Inscripcion.estado == INSCRIPCION_ALTA,
        )
        .count()
    )
    asistencias = (
        db.query(Asistencia)
        .filter(Asistencia.actividad_id == actividad.id)
        .count()
    )
    respuestas = (
        db.query(RespuestaEncuesta)
        .options(
            joinedload(RespuestaEncuesta.estudiante)
            .joinedload(Estudiante.user)
            .joinedload(User.persona)
        )
        .filter(RespuestaEncuesta.actividad_id == actividad.id)
        .order_by(RespuestaEncuesta.id)
        .all()
    )
    return {
        "inscriptos": inscriptos,
        "asistencias": asistencias,
        "duracion": formatear_duracion(actividad.fecha_inicio, actividad.fecha_fin),
        "respuestas": respuestas,
    }

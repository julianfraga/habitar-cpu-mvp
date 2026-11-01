"""Survey completion checks used by post-activity credit awards."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Actividad, RespuestaEncuesta


def preparar_respuestas(
    actividad: Actividad,
    respuestas: list[str],
) -> dict[str, str]:
    preguntas = actividad.preguntas or {}
    claves = sorted(preguntas, key=lambda clave: int(clave[1:]))
    if not claves or len(respuestas) != len(claves):
        raise ValueError("Respondé todas las preguntas de la encuesta.")

    respuestas_limpias = [respuesta.strip() for respuesta in respuestas]
    if any(not respuesta for respuesta in respuestas_limpias):
        raise ValueError("Todas las respuestas son obligatorias.")
    return dict(zip(claves, respuestas_limpias))


def estudiante_completo_encuesta(
    db: Session, estudiante_id: int, actividad_id: int
) -> bool:
    actividad = db.get(Actividad, actividad_id)
    if actividad is None:
        return False
    if not actividad.encuesta_obligatoria:
        return True
    return (
        db.query(RespuestaEncuesta.id)
        .filter(
            RespuestaEncuesta.estudiante_id == estudiante_id,
            RespuestaEncuesta.actividad_id == actividad_id,
        )
        .first()
        is not None
    )

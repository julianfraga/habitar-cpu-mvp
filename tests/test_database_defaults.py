from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.models import Actividad, Inscripcion, Notification, Persona, User


def test_direct_sql_inserts_use_database_defaults(db_session):
    persona = Persona(
        nombre="Importado",
        apellido="Alumno",
        email="importado@example.com",
    )
    db_session.add(persona)
    db_session.flush()

    user_id = db_session.execute(
        text(
            "INSERT INTO users (persona_id, pw_hash) "
            "VALUES (:persona_id, :pw_hash) RETURNING id"
        ),
        {"persona_id": persona.id, "pw_hash": "hashed-password"},
    ).scalar_one()
    now = datetime.now(timezone.utc)
    activity_id = db_session.execute(
        text(
            "INSERT INTO actividades (titulo, fecha_inicio, fecha_fin) "
            "VALUES (:titulo, :fecha_inicio, :fecha_fin) RETURNING id"
        ),
        {
            "titulo": "Actividad importada",
            "fecha_inicio": (now + timedelta(days=1)).isoformat(),
            "fecha_fin": (now + timedelta(days=1, hours=1)).isoformat(),
        },
    ).scalar_one()
    inscription_id = db_session.execute(
        text(
            "INSERT INTO inscripciones (actividad_id, user_id) "
            "VALUES (:actividad_id, :user_id) RETURNING id"
        ),
        {"actividad_id": activity_id, "user_id": user_id},
    ).scalar_one()
    notification_id = db_session.execute(
        text(
            "INSERT INTO notifications (user_id, mensaje) "
            "VALUES (:user_id, :mensaje) RETURNING id"
        ),
        {"user_id": user_id, "mensaje": "Notificación"},
    ).scalar_one()
    db_session.flush()

    user = db_session.get(User, user_id)
    activity = db_session.get(Actividad, activity_id)
    inscription = db_session.get(Inscripcion, inscription_id)
    notification = db_session.get(Notification, notification_id)

    assert user is not None
    assert (user.rol, user.debe_cambiar_pw) == ("estudiante", True)
    assert activity is not None
    assert (
        activity.descripcion,
        activity.tipo,
        activity.lugar,
        activity.creditos,
        activity.preguntas,
        activity.cupo_max,
        activity.estado,
    ) == ("", "presencial", "", 1, {}, 30, "borrador")
    assert inscription is not None
    assert (inscription.estado, inscription.reminded, inscription.baja_penalizada) == (
        "inscripto",
        False,
        False,
    )
    assert notification is not None
    assert notification.leido is False

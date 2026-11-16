from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, delete, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Actividad, Estudiante, Persona, User
from app.models.inscripcion import Inscripcion
from app.models.mensaje import Mensaje
from app.models.respuesta_encuesta import RespuestaEncuesta


@pytest.mark.parametrize("parent", ["user", "persona", "activity"])
@pytest.mark.parametrize("delete_path", ["sql", "orm"])
def test_deleting_parent_with_history_is_restricted(parent, delete_path):
    engine = create_engine("sqlite://", poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        user = User(
            persona=Persona(nombre="Ana", apellido="Prueba", email="ana@example.com"),
            pw_hash="hashed-password",
            rol="estudiante",
            estudiante=Estudiante(),
        )
        activity = Actividad(
            titulo="Actividad",
            fecha_inicio=now + timedelta(days=1),
            fecha_fin=now + timedelta(days=1, hours=1),
            creditos=Decimal("1.0"),
        )
        session.add_all([user, activity])
        session.flush()
        session.add_all(
            [
                Inscripcion(actividad_id=activity.id, user_id=user.id),
                Mensaje(
                    remitente_id=user.id,
                    asunto="Historial",
                    cuerpo="Mensaje conservado",
                ),
                RespuestaEncuesta(
                    actividad_id=activity.id,
                    estudiante_id=user.id,
                    rating=5,
                    respuestas={},
                ),
            ]
        )
        session.commit()
        user_id, persona_id, activity_id = user.id, user.persona_id, activity.id

    targets = {
        "user": (User.__table__, User, User.id, user_id),
        "persona": (Persona.__table__, Persona, Persona.id, persona_id),
        "activity": (Actividad.__table__, Actividad, Actividad.id, activity_id),
    }
    table, model, primary_key, identifier = targets[parent]
    if delete_path == "sql":
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(delete(table).where(primary_key == identifier))
    else:
        with Session(engine) as session:
            instance = session.get(model, identifier)
            assert instance is not None
            session.delete(instance)
            with pytest.raises(IntegrityError):
                session.flush()
            session.rollback()

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Inscripcion)) == 1
        assert session.scalar(select(func.count()).select_from(Mensaje)) == 1
        assert session.scalar(select(func.count()).select_from(RespuestaEncuesta)) == 1

    engine.dispose()

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models import (
    Actividad,
    Asistencia,
    Carrera,
    Docente,
    Estudiante,
    Faq,
    Inscripcion,
    Mensaje,
    Persona,
    ROL_COORDINACION,
    TipoCarrera,
    User,
)
from app.seed import CARRERAS, COORDINATOR_EMAIL, seed_all
from app.security import hash_password, verify_password


def test_seed_creates_only_coordinator_and_listed_careers(db_session, monkeypatch):
    password = "configured-test-password"
    monkeypatch.setattr(settings, "DEMO_PASSWORD", password)

    seed_all(db_session)

    user = db_session.scalar(
        select(User).join(Persona).where(Persona.email == COORDINATOR_EMAIL)
    )
    assert user is not None
    assert user.rol == ROL_COORDINACION
    assert verify_password(password, user.pw_hash)
    assert db_session.scalar(select(func.count()).select_from(User)) == 1
    assert {
        carrera.nombre for carrera in db_session.scalars(select(Carrera))
    } == {nombre for nombre, _, _ in CARRERAS}
    assert {"Ingeniería", "Licenciatura"} <= {
        tipo.nombre for tipo in db_session.scalars(select(TipoCarrera))
    }

    for model in (Actividad, Asistencia, Docente, Estudiante, Faq, Inscripcion, Mensaje):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0

    user.pw_hash = hash_password("outdated-password")
    db_session.commit()
    seed_all(db_session)

    assert db_session.scalar(select(func.count()).select_from(User)) == 1
    assert db_session.scalar(select(func.count()).select_from(Carrera)) == len(CARRERAS)
    assert verify_password(password, user.pw_hash)


def test_seed_requires_demo_password_before_writing(db_session, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_PASSWORD", "")

    with pytest.raises(RuntimeError, match="DEMO_PASSWORD"):
        seed_all(db_session)

    assert db_session.scalar(select(func.count()).select_from(User)) == 0
    assert db_session.scalar(select(func.count()).select_from(Carrera)) == 0

from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select

from app.config import settings
import app.seed as seed_module
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


def test_seed_module_entrypoint_runs_seed_in_session(monkeypatch):
    session = object()
    session_context = MagicMock()
    session_context.__enter__.return_value = session
    session_factory = MagicMock(return_value=session_context)
    seed_mock = MagicMock()
    monkeypatch.setattr(seed_module, "SessionLocal", session_factory)
    monkeypatch.setattr(seed_module, "seed_all", seed_mock)

    seed_module.main()

    session_factory.assert_called_once_with()
    seed_mock.assert_called_once_with(session)
    session_context.__exit__.assert_called_once()

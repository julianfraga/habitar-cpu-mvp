from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import (
    ESTADO_PUBLICADA,
    INSCRIPCION_ALTA,
    INSCRIPCION_BAJA,
    Inscripcion,
)
from app.security import hash_password
from app.services.inscripcion import (
    revocar_penalizaciones_reprogramacion,
)


def _hours_before_start_for_open_unpenalized_activity():
    return 2 * max(
        settings.MARGEN_BAJA_HORAS,
        settings.CIERRE_INSCRIPCIONES_HORAS,
    )


@pytest.fixture
def student_flow_client(db_session, user_factory, carrera_factory):
    carrera = carrera_factory()
    user = user_factory(email="student-flow@example.com")
    user.pw_hash = hash_password("password123")
    user.carrera_id = carrera.id
    user.debe_cambiar_pw = False
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, follow_redirects=False) as client:
            login = client.post(
                "/login",
                data={"email": user.email, "password": "password123"},
            )
            assert login.status_code == 303
            yield client, db_session, user, carrera
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(
    "hours_before, shows_warning",
    [
        (settings.MARGEN_BAJA_HORAS * 2 + 1, False),
        (settings.MARGEN_BAJA_HORAS + 1, False),
        (max(settings.MARGEN_BAJA_HORAS - 1, 0.5), settings.MARGEN_BAJA_HORAS > 0),
    ],
)
def test_activity_detail_warns_before_penalized_cancellation(
    db_session,
    user_factory,
    carrera_factory,
    actividad_factory,
    hours_before,
    shows_warning,
):
    user = user_factory(email="student@example.com")
    user.pw_hash = hash_password("password123")
    user.carrera_id = carrera_factory().id
    user.debe_cambiar_pw = False
    activity = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=datetime.now(timezone.utc) + timedelta(hours=hours_before),
    )
    db_session.add(
        Inscripcion(
            actividad_id=activity.id,
            user_id=user.id,
            estado=INSCRIPCION_ALTA,
        )
    )
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, follow_redirects=False) as client:
            login = client.post(
                "/login",
                data={"email": user.email, "password": "password123"},
            )
            response = client.get(f"/actividades/{activity.id}")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert login.status_code == 303
    assert response.status_code == 200
    assert ("deberás acreditar 1 punto más por baja tardía" in response.text) is shows_warning


def test_closed_enrollment_disables_registration_and_shows_badge(
    db_session, user_factory, carrera_factory, actividad_factory
):
    carrera = carrera_factory()
    user = user_factory(email="student-closed@example.com")
    user.pw_hash = hash_password("password123")
    user.carrera_id = carrera.id
    user.debe_cambiar_pw = False
    activity = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=datetime.now(timezone.utc)
        + timedelta(hours=settings.CIERRE_INSCRIPCIONES_HORAS),
        carreras=[carrera],
    )
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, follow_redirects=False) as client:
            client.post(
                "/login",
                data={"email": user.email, "password": "password123"},
            )
            detail = client.get(f"/actividades/{activity.id}")
            listing = client.get("/actividades")
            enroll = client.post(f"/actividades/{activity.id}/inscribir")
            error_page = client.get(enroll.headers["location"])
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert '<button type="button" disabled' in detail.text
    assert enroll.status_code == 303
    query = parse_qs(urlsplit(enroll.headers["location"]).query)
    assert "msg" not in query and "err" not in query
    assert "inscripción a esta actividad ya está cerrada" in error_page.text


@pytest.mark.parametrize(
    "journey",
    ["stays_enrolled", "early_cancellation", "late_cancellation", "reprogrammed"],
)
def test_student_enrollment_and_cancellation_journeys(
    student_flow_client, actividad_factory, journey
):
    client, db_session, user, carrera = student_flow_client
    now = datetime.now(timezone.utc)
    if journey == "late_cancellation":
        if settings.MARGEN_BAJA_HORAS <= settings.CIERRE_INSCRIPCIONES_HORAS:
            pytest.skip("No hay intervalo abierto para inscribirse y luego dar una baja tardía.")
        hours_before_start = (
            settings.MARGEN_BAJA_HORAS + settings.CIERRE_INSCRIPCIONES_HORAS
        ) / 2
        reprogrammed = False
        expected_penalty = True
    elif journey == "reprogrammed":
        if max(
            settings.MARGEN_BAJA_HORAS,
            settings.CIERRE_INSCRIPCIONES_HORAS,
        ) == 0:
            pytest.skip("No hay intervalo futuro con los umbrales configurados en 0.")
        hours_before_start = min(
            settings.MARGEN_BAJA_HORAS / 2
            if settings.MARGEN_BAJA_HORAS > 0
            else settings.CIERRE_INSCRIPCIONES_HORAS / 2,
            settings.CIERRE_INSCRIPCIONES_HORAS / 2
            if settings.CIERRE_INSCRIPCIONES_HORAS > 0
            else settings.MARGEN_BAJA_HORAS / 2,
        )
        reprogrammed = True
        expected_penalty = False
    else:
        hours_before_start = _hours_before_start_for_open_unpenalized_activity()
        if hours_before_start == 0:
            pytest.skip("No hay intervalo futuro con los umbrales configurados en 0.")
        reprogrammed = False
        expected_penalty = False

    activity = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now + timedelta(hours=hours_before_start),
        carreras=[carrera],
    )
    activity.reprogramada_corto_plazo = reprogrammed
    db_session.commit()

    enroll = client.post(f"/actividades/{activity.id}/inscribir")
    assert enroll.status_code == 303
    confirmation = client.get(enroll.headers["location"])
    assert "¡Inscripción confirmada!" in confirmation.text

    detail = client.get(f"/actividades/{activity.id}")
    shows_penalty_warning = (
        "deberás acreditar 1 punto más por baja tardía" in detail.text
    )
    assert shows_penalty_warning is expected_penalty

    enrollment = db_session.query(Inscripcion).one()
    assert enrollment.estado == INSCRIPCION_ALTA
    if journey == "stays_enrolled":
        home = client.get("/home")
        assert activity.titulo in home.text
        return

    unenroll = client.post(f"/actividades/{activity.id}/baja")
    assert unenroll.status_code == 303
    result = client.get(unenroll.headers["location"])
    db_session.refresh(user.estudiante)
    db_session.refresh(enrollment)

    assert enrollment.estado == INSCRIPCION_BAJA
    assert enrollment.baja_penalizada is expected_penalty
    assert user.estudiante.creditos_penalizacion == (
        1.0 if expected_penalty else 0.0
    )
    if expected_penalty:
        assert "Se sumó 1 crédito requerido" in result.text
    else:
        assert "Liberaste tu cupo" in result.text


@pytest.mark.parametrize(
    "journey",
    [
        "open_first_registration",
        "closed_first_registration",
        "penalized_same_activity",
        "closed_after_unpenalized_baja",
        "reprogrammed_after_penalty",
    ],
)
def test_student_registration_open_penalty_and_reprogramming_paths(
    student_flow_client, actividad_factory, journey
):
    client, db_session, user, carrera = student_flow_client
    now = datetime.now(timezone.utc)
    if journey in {"closed_first_registration", "closed_after_unpenalized_baja"}:
        if settings.CIERRE_INSCRIPCIONES_HORAS == 0:
            pytest.skip("Con cierre en 0 horas no hay período futuro de inscripción cerrada.")
        hours_before_start = settings.CIERRE_INSCRIPCIONES_HORAS / 2
        reprogrammed = False
    elif journey == "reprogrammed_after_penalty":
        if max(
            settings.MARGEN_BAJA_HORAS,
            settings.CIERRE_INSCRIPCIONES_HORAS,
        ) == 0:
            pytest.skip("No hay intervalo futuro con los umbrales configurados en 0.")
        hours_before_start = (
            settings.CIERRE_INSCRIPCIONES_HORAS / 2
            if settings.CIERRE_INSCRIPCIONES_HORAS > 0
            else settings.MARGEN_BAJA_HORAS / 2
        )
        reprogrammed = True
    else:
        hours_before_start = _hours_before_start_for_open_unpenalized_activity()
        if hours_before_start == 0:
            pytest.skip("No hay intervalo futuro con los umbrales configurados en 0.")
        reprogrammed = False

    activity = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now + timedelta(hours=hours_before_start),
        carreras=[carrera],
    )
    activity.reprogramada_corto_plazo = reprogrammed
    db_session.commit()

    has_prior_baja = journey in {
        "penalized_same_activity",
        "closed_after_unpenalized_baja",
        "reprogrammed_after_penalty",
    }
    was_penalized = journey in {
        "penalized_same_activity",
        "reprogrammed_after_penalty",
    }
    if has_prior_baja:
        db_session.add(
            Inscripcion(
                actividad_id=activity.id,
                user_id=user.id,
                estado=INSCRIPCION_BAJA,
                baja_penalizada=was_penalized,
            )
        )
        if was_penalized:
            user.estudiante.creditos_penalizacion = 1.0
        db_session.commit()

    if journey == "reprogrammed_after_penalty":
        assert revocar_penalizaciones_reprogramacion(db_session, activity) == 1

    response = client.post(f"/actividades/{activity.id}/inscribir")
    assert response.status_code == 303
    result = client.get(response.headers["location"])
    enrollment = db_session.query(Inscripcion).one_or_none()
    db_session.refresh(user.estudiante)

    if journey in {"open_first_registration", "reprogrammed_after_penalty"}:
        assert enrollment is not None
        assert enrollment.estado == INSCRIPCION_ALTA
        assert user.estudiante.creditos_penalizacion == 0.0
        assert "¡Inscripción confirmada!" in result.text
        assert not enrollment.baja_penalizada
    else:
        assert enrollment is None or enrollment.estado == INSCRIPCION_BAJA
        expected_error = (
            "inscripción a esta actividad ya está cerrada"
            if journey
            in {
                "closed_first_registration",
                "closed_after_unpenalized_baja",
            }
            else "baja fue penalizada"
        )
        assert expected_error in result.text.lower()


def test_finalized_activity_shows_badge_and_cannot_be_unenrolled(
    db_session, user_factory, carrera_factory, actividad_factory
):
    carrera = carrera_factory()
    user = user_factory(email="student-finished@example.com")
    user.pw_hash = hash_password("password123")
    user.carrera_id = carrera.id
    user.debe_cambiar_pw = False
    activity = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=datetime.now(timezone.utc) - timedelta(hours=4),
        carreras=[carrera],
    )
    activity.fecha_fin = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add(
        Inscripcion(
            actividad_id=activity.id,
            user_id=user.id,
            estado=INSCRIPCION_ALTA,
        )
    )
    db_session.commit()
    db_session.refresh(activity)
    assert activity.finalizada

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, follow_redirects=False) as client:
            client.post(
                "/login",
                data={"email": user.email, "password": "password123"},
            )
            detail = client.get(f"/actividades/{activity.id}")
            listing = client.get("/actividades")
            unenroll = client.post(f"/actividades/{activity.id}/baja")
            error_page = client.get(unenroll.headers["location"])
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert "finalizada" in detail.text.lower()
    assert "No es posible darse de baja" in detail.text
    assert "/baja" not in detail.text
    assert "finalizada" in listing.text.lower()
    assert unenroll.status_code == 303
    query = parse_qs(urlsplit(unenroll.headers["location"]).query)
    assert "msg" not in query and "err" not in query
    assert "actividad ya finalizada" in error_page.text


def test_inscription_confirmation_shows_cancellation_policy_below_banner(
    db_session, user_factory, carrera_factory, actividad_factory
):
    if _hours_before_start_for_open_unpenalized_activity() == 0:
        pytest.skip("No hay intervalo futuro con los umbrales configurados en 0.")
    user = user_factory(email="student@example.com")
    user.pw_hash = hash_password("password123")
    user.carrera_id = carrera_factory().id
    user.debe_cambiar_pw = False
    activity = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=datetime.now(timezone.utc)
        + timedelta(
            hours=_hours_before_start_for_open_unpenalized_activity()
        ),
    )
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, follow_redirects=True) as client:
            client.post(
                "/login",
                data={"email": user.email, "password": "password123"},
            )
            response = client.post(f"/actividades/{activity.id}/inscribir")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    confirmation_position = response.text.index("¡Inscripción confirmada!")
    reminder_position = response.text.index(
        f"Podés darte de baja sin penalización con al menos "
        f"{settings.MARGEN_BAJA_HORAS} horas de anticipación."
    )
    assert confirmation_position < reminder_position
    assert (
        f"Con menos de {settings.MARGEN_BAJA_HORAS} horas se suma 1 crédito requerido; "
        "si la actividad fue reprogramada, "
        "la baja no tiene penalización."
        in response.text
    )


def test_activity_sort_links_preserve_filters_and_toggle_direction(
    db_session, user_factory, carrera_factory, actividad_factory
):
    carrera = carrera_factory()
    user = user_factory(email="student-sort@example.com")
    user.pw_hash = hash_password("password123")
    user.carrera_id = carrera.id
    user.debe_cambiar_pw = False
    actividad_factory(
        estado=ESTADO_PUBLICADA,
        tipo="virtual",
        carreras=[carrera],
        fecha_inicio=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, follow_redirects=False) as client:
            login = client.post(
                "/login",
                data={"email": user.email, "password": "password123"},
            )
            response = client.get(
                "/actividades",
                params={
                    "tipo": "virtual",
                    "sort": "cupo",
                    "direction": "desc",
                },
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert login.status_code == 303
    assert response.status_code == 200
    assert "tipo=virtual&amp;sort=cupo&amp;direction=asc" in response.text
    assert "aria-pressed=\"true\"" in response.text

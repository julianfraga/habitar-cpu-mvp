from datetime import datetime, timedelta, timezone
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import (
    Asistencia,
    Docente,
    Estudiante,
    ESTADO_BORRADOR,
    ESTADO_CANCELADA,
    ESTADO_CREDITOS_ACREDITADO,
    ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
    ESTADO_PUBLICADA,
    Actividad,
    Inscripcion,
    INSCRIPCION_ALTA,
    Persona,
    User,
)
from app.security import hash_password
from app.services.parsing import parse_duracion, parse_intervalo_tiempo
from app.templating import _fmt_dt
from app.services.credits import accumulated_credits


@pytest.fixture
def admin_actividades_client(db_session, user_factory, carrera_factory):
    admin = user_factory(
        rol="coordinacion",
        email="coordinacion@unsam.edu.ar",
    )
    admin.pw_hash = hash_password("habitar123")
    docente = user_factory(rol="docente", email="docente@unsam.edu.ar")
    carrera = carrera_factory()
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, follow_redirects=False)
    login_response = client.post(
        "/login",
        data={"email": admin.email, "password": "habitar123"},
    )
    assert login_response.status_code == 303
    yield client, db_session, docente, carrera
    client.close()
    app.dependency_overrides.pop(get_db, None)


def actividad_form_data(docente_id, carrera_id, *, titulo="Actividad nueva"):
    return {
        "titulo": titulo,
        "descripcion": "Descripción de prueba",
        "tipo": "presencial",
        "fecha_inicio": "2030-01-10T10:00",
        "fecha_fin": "2030-01-10T12:00",
        "lugar": "Campus Miguelete",
        "docentes_ids": str(docente_id),
        "docentes_nombres": ["Eva"],
        "docentes_apellidos": ["Invitada"],
        "docentes_emails": [" EVA@Example.com "],
        "creditos": "2.5",
        "cupo_max": "20",
        "encuesta_obligatoria": "true",
        "preguntas": ["¿Qué te pareció la actividad?"],
        "carreras_asociadas": str(carrera_id),
    }


def assert_flash_redirect(client, response, expected_message):
    location = urlsplit(response.headers["location"])
    query = parse_qs(location.query)
    assert "msg" not in query
    assert "err" not in query
    assert "notice" not in query
    page = client.get(response.headers["location"])
    assert expected_message in page.text
    return page


def table_row(response, activity_title):
    rows = re.findall(r"<tr\b.*?</tr>", response.text, flags=re.DOTALL)
    return next(row for row in rows if activity_title in row)


def testparse_duracion_accepts_hh_mm():
    assert parse_duracion("02:15") == timedelta(hours=2, minutes=15)


def testparse_duracion_rejects_invalid_format():
    with pytest.raises(ValueError, match="HH:MM"):
        parse_duracion("2:15")


def test_parse_dates_rejects_dates_before_today():
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)

    with pytest.raises(ValueError, match="anteriores al día de hoy"):
        parse_intervalo_tiempo(
            f"{yesterday.isoformat()}T10:00",
            duracion="01:00",
            modo_finalizacion="duracion",
        )


def test_parse_activity_times_uses_argentina_timezone_and_round_trips_locally():
    inicio, fin = parse_intervalo_tiempo(
        "2030-01-10T15:00",
        duracion="02:30",
        modo_finalizacion="duracion",
    )

    assert inicio == datetime(2030, 1, 10, 18, tzinfo=timezone.utc)
    assert fin == datetime(2030, 1, 10, 20, 30, tzinfo=timezone.utc)
    assert _fmt_dt(inicio, "%Y-%m-%dT%H:%M") == "2030-01-10T15:00"
    assert _fmt_dt(fin, "%Y-%m-%dT%H:%M") == "2030-01-10T17:30"


def test_admin_activities_pages_require_coordination_role(
    db_session, user_factory, carrera_factory
):
    student = user_factory(email="alumno@example.com")
    student.pw_hash = hash_password("student-password")
    student.carrera_id = carrera_factory().id
    student.debe_cambiar_pw = False
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app, follow_redirects=False)
        login_response = client.post(
            "/login",
            data={"email": student.email, "password": "student-password"},
        )
        response = client.get("/admin/actividades")
        client.close()
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert login_response.status_code == 303
    assert response.status_code == 403


def test_admin_activities_crud_lifecycle(admin_actividades_client):
    client, db_session, docente, carrera = admin_actividades_client

    new_page = client.get("/admin/actividades/nueva")
    assert new_page.status_code == 200
    assert "Nueva actividad" in new_page.text
    assert 'aria-label="Eliminar pregunta"' in new_page.text
    assert 'title="Pregunta' not in new_page.text

    create_response = client.post(
        "/admin/actividades",
        data=actividad_form_data(docente.docente_id, carrera.id),
    )
    assert create_response.status_code == 303

    actividad = db_session.query(Actividad).one()
    assert actividad.titulo == "Actividad nueva"
    assert {d.nombre_completo for d in actividad.docentes} == {
        docente.docente.nombre_completo,
        "Eva Invitada",
    }
    eva = next(d for d in actividad.docentes if d.nombre_completo == "Eva Invitada")
    assert eva.persona.email == "eva@example.com"
    assert actividad.creditos == 2.5
    assert actividad.carreras_asociadas == [carrera]

    panel_response = client.get(
        "/admin/actividades",
        params={"carreras_asociadas": str(carrera.id)},
    )
    assert panel_response.status_code == 200
    assert f"carreras_asociadas={carrera.id}&amp;sort=nombre&amp;direction=asc" in panel_response.text
    sorted_panel_response = client.get(
        "/admin/actividades",
        params={
            "carreras_asociadas": str(carrera.id),
            "sort": "fecha",
            "direction": "desc",
        },
    )
    assert sorted_panel_response.status_code == 200
    assert f"carreras_asociadas={carrera.id}&amp;sort=fecha&amp;direction=asc" in sorted_panel_response.text

    edit_response = client.get(f"/admin/actividades/{actividad.id}/editar")
    assert edit_response.status_code == 200
    assert actividad.titulo in edit_response.text
    assert 'name="fecha_inicio"\n          value="2030-01-10T10:00"' in edit_response.text
    assert 'name="fecha_fin"\n          value="2030-01-10T12:00"' in edit_response.text
    assert f'value="{docente.docente_id}" selected' in edit_response.text
    assert f'data-id="{carrera.id}"' in edit_response.text

    update_data = actividad_form_data(docente.docente_id, carrera.id, titulo="Actividad actualizada")
    update_data["creditos"] = "5"
    update_response = client.post(
        f"/admin/actividades/{actividad.id}",
        data=update_data,
    )
    assert update_response.status_code == 303
    db_session.refresh(actividad)
    assert actividad.titulo == "Actividad actualizada"
    assert actividad.creditos == 5
    eva = next(d for d in actividad.docentes if d.nombre_completo == "Eva Invitada")
    assert eva.persona.email == "eva@example.com"

    preview_response = client.get(f"/admin/actividades/{actividad.id}/preview")
    assert preview_response.status_code == 200
    assert "Actividad actualizada" in preview_response.text

    publish_response = client.post(f"/admin/actividades/{actividad.id}/publicar")
    assert publish_response.status_code == 303
    assert_flash_redirect(client, publish_response, "Actividad publicada")
    db_session.refresh(actividad)
    assert actividad.estado == ESTADO_PUBLICADA
    cancel_response = client.post(f"/admin/actividades/{actividad.id}/cancelar")
    assert cancel_response.status_code == 303
    assert_flash_redirect(client, cancel_response, "Actividad cancelada")
    db_session.refresh(actividad)
    assert actividad.estado == ESTADO_CANCELADA


def test_panel_shows_single_badge_when_activity_includes_all_careers(
    admin_actividades_client, carrera_factory
):
    client, _db_session, docente, carrera = admin_actividades_client
    otra_carrera = carrera_factory(nombre="Psicología")
    data = actividad_form_data(docente.docente_id, carrera.id)
    data["carreras_asociadas"] = [str(carrera.id), str(otra_carrera.id)]

    create_response = client.post("/admin/actividades", data=data)
    assert create_response.status_code == 303

    partial_data = actividad_form_data(
        docente.docente_id, carrera.id, titulo="Actividad parcial"
    )
    partial_response = client.post("/admin/actividades", data=partial_data)
    assert partial_response.status_code == 303

    panel_response = client.get("/admin/actividades")
    assert panel_response.status_code == 200
    activity_row = table_row(panel_response, "Actividad nueva")
    assert "Todas las carreras" in activity_row
    assert "Arquitectura" not in activity_row
    assert "Psicología" not in activity_row
    partial_row = table_row(panel_response, "Actividad parcial")
    assert "Arquitectura" in partial_row
    assert "Todas las carreras" not in partial_row


def test_finalized_activity_panel_shows_inscriptions_attendance_and_duplicate_action(
    admin_actividades_client, user_factory,
):
    client, db_session, _docente, carrera = admin_actividades_client
    fecha_inicio = datetime.now(timezone.utc) - timedelta(hours=4)
    actividad = Actividad(
        titulo="Actividad finalizada",
        descripcion="Descripción",
        tipo="presencial",
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_inicio + timedelta(hours=2),
        lugar="Campus",
        cupo_max=30,
        estado=ESTADO_PUBLICADA,
        carreras_asociadas=[carrera],
    )
    db_session.add(actividad)
    db_session.commit()
    student = user_factory(rol="estudiante", email="inscripto@example.com")
    db_session.add(
        Inscripcion(
            actividad_id=actividad.id,
            user_id=student.id,
            estado=INSCRIPCION_ALTA,
        )
    )
    db_session.commit()

    response = client.get("/admin/actividades")

    assert response.status_code == 200
    row = table_row(response, "Actividad finalizada")
    print(row)
    assert "Inscriptos" in row
    assert "Asistencia" in row
    assert "Ver encuestas" in row
    assert f"/admin/analytics/actividad_{actividad.id}" in row
    assert "Publicar otra igual" in row
    assert "Vista previa" not in row
    assert "Editar" not in row
    assert "Cancelar" not in row
    assert f"copiar_de={actividad.id}" in row

    inscriptos_response = client.get(
        f"/admin/actividades/{actividad.id}/inscriptos"
    )
    assert inscriptos_response.status_code == 200
    assert "inscripto@example.com" in inscriptos_response.text


def test_duplicate_activity_form_copies_settings_but_clears_dates(
    admin_actividades_client,
):
    client, db_session, _docente, carrera = admin_actividades_client
    fecha_inicio = datetime.now(timezone.utc) - timedelta(hours=4)
    actividad = Actividad(
        titulo="Actividad para repetir",
        descripcion="Descripción copiada",
        tipo="presencial",
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_inicio + timedelta(hours=2),
        lugar="Campus",
        cupo_max=24,
        creditos=2.5,
        estado=ESTADO_PUBLICADA,
        encuesta_obligatoria=True,
        preguntas={"q1": "¿Qué te pareció?"},
        carreras_asociadas=[carrera],
    )
    db_session.add(actividad)
    db_session.commit()

    response = client.get(
        f"/admin/actividades/nueva?copiar_de={actividad.id}"
    )

    assert response.status_code == 200
    assert "Datos copiados de «Actividad para repetir»" in response.text
    assert 'name="titulo"' in response.text
    assert 'value="Actividad para repetir"' in response.text
    assert 'name="descripcion"' in response.text
    assert "Descripción copiada" in response.text
    assert 'name="duracion"' in response.text
    assert 'value="02:00"' in response.text
    inicio = response.text.split('id="fecha_inicio"', 1)[1].split(">", 1)[0]
    assert 'value=""' in inicio


def test_create_activity_rejects_credits_not_in_half_point_steps(admin_actividades_client):
    client, db_session, docente, carrera = admin_actividades_client
    data = actividad_form_data(docente.docente_id, carrera.id)
    data["creditos"] = "1.3"

    response = client.post("/admin/actividades", data=data)

    assert response.status_code == 303
    assert_flash_redirect(client, response, "múltiplo de 0,5")
    assert db_session.query(Actividad).count() == 0


def test_create_activity_rejects_more_than_five_survey_questions(
    admin_actividades_client,
):
    client, db_session, docente, carrera = admin_actividades_client
    data = actividad_form_data(docente.docente_id, carrera.id)
    data["preguntas"] = [f"Pregunta {index}" for index in range(1, 7)]

    response = client.post("/admin/actividades", data=data)

    assert response.status_code == 422
    assert db_session.query(Actividad).count() == 0


def test_create_activity_ignores_empty_survey_questions(admin_actividades_client):
    client, db_session, docente, carrera = admin_actividades_client
    data = actividad_form_data(docente.docente_id, carrera.id)
    data["preguntas"] = ["Pregunta 1", "", "  ", "Pregunta 2"]

    response = client.post("/admin/actividades", data=data)

    assert response.status_code == 303
    actividad = db_session.query(Actividad).one()
    assert actividad.preguntas == {"q1": "Pregunta 1", "q2": "Pregunta 2"}


def test_user_with_matching_name_keeps_separate_persona_from_docente(
    db_session, user_factory
):
    staff = user_factory(rol="docente")
    student = User(
        persona=Persona(
            email="coincide@example.com",
            nombre=staff.nombre,
            apellido=staff.apellido,
        ),
        pw_hash="test-hash",
        estudiante=Estudiante(),
    )
    db_session.add(student)
    db_session.commit()

    assert db_session.query(Docente).count() == 1
    assert staff.docente_id is not None
    assert student.docente_id is None


def test_create_activity_with_invalid_dates_redirects_with_error(admin_actividades_client):
    client, db_session, docente, carrera = admin_actividades_client
    data = actividad_form_data(docente.docente_id, carrera.id)
    data["fecha_fin"] = "2030-01-10T09:00"

    response = client.post("/admin/actividades", data=data)

    assert response.status_code == 303
    assert_flash_redirect(client, response, "Fechas inválidas")
    assert db_session.query(Actividad).count() == 0


@pytest.mark.parametrize(
    ("invalid_field", "expected_error"),
    [
        ("fecha_fin", "Fechas inválidas: revisá inicio y fin."),
        ("creditos", "múltiplo de 0,5"),
        ("carreras_asociadas", "No se puede crear una actividad sin carreras asociadas."),
    ],
)
def test_update_activity_validation_errors_render_on_edit_form(
    admin_actividades_client, invalid_field, expected_error
):
    client, db_session, docente, carrera = admin_actividades_client
    create_response = client.post(
        "/admin/actividades",
        data=actividad_form_data(docente.docente_id, carrera.id),
    )
    assert create_response.status_code == 303
    actividad = db_session.query(Actividad).one()

    update_data = actividad_form_data(
        docente.docente_id, carrera.id, titulo="Cambios sin guardar"
    )
    if invalid_field == "fecha_fin":
        update_data["fecha_fin"] = "2030-01-10T09:00"
    elif invalid_field == "creditos":
        update_data["creditos"] = "1.3"
    else:
        update_data.pop("carreras_asociadas")
    response = client.post(f"/admin/actividades/{actividad.id}", data=update_data)

    assert response.status_code == 200
    assert "location" not in response.headers
    assert "Editar actividad" in response.text
    assert 'role="alert"' in response.text
    assert expected_error in response.text
    assert "Cambios sin guardar" in response.text
    if invalid_field == "fecha_fin":
        assert 'value="2030-01-10T09:00"' in response.text
    db_session.refresh(actividad)
    assert actividad.titulo == "Actividad nueva"


def test_update_activity_persists_and_renders_argentina_start_and_end_times(
    admin_actividades_client,
):
    client, db_session, docente, carrera = admin_actividades_client
    create_response = client.post(
        "/admin/actividades",
        data=actividad_form_data(docente.docente_id, carrera.id),
    )
    assert create_response.status_code == 303
    activity = db_session.query(Actividad).one()

    update_data = actividad_form_data(docente.docente_id, carrera.id)
    update_data.update(
        fecha_inicio="2030-01-10T15:00",
        fecha_fin="",
        duracion="02:30",
        modo_finalizacion="duracion",
    )
    update_response = client.post(
        f"/admin/actividades/{activity.id}",
        data=update_data,
    )

    assert update_response.status_code == 303
    db_session.refresh(activity)
    stored_start = activity.fecha_inicio
    stored_end = activity.fecha_fin
    if stored_start.tzinfo is None:
        stored_start = stored_start.replace(tzinfo=timezone.utc)
    if stored_end.tzinfo is None:
        stored_end = stored_end.replace(tzinfo=timezone.utc)
    assert stored_start == datetime(2030, 1, 10, 18, tzinfo=timezone.utc)
    assert stored_end == datetime(2030, 1, 10, 20, 30, tzinfo=timezone.utc)

    edit_response = client.get(f"/admin/actividades/{activity.id}/editar")
    assert edit_response.status_code == 200
    assert 'value="2030-01-10T15:00"' in edit_response.text
    assert 'value="2030-01-10T17:30"' in edit_response.text


def test_activity_without_career_cannot_be_published(admin_actividades_client):
    client, db_session, docente, _ = admin_actividades_client
    data = actividad_form_data(docente.id, 0)
    data.pop("carreras_asociadas")

    create_response = client.post("/admin/actividades", data=data)

    assert create_response.status_code == 303
    actividad = db_session.query(Actividad).one()
    assert actividad.estado == ESTADO_BORRADOR
    assert actividad.carreras_asociadas == []

    publish_response = client.post(f"/admin/actividades/{actividad.id}/publicar")

    assert publish_response.status_code == 303
    assert_flash_redirect(client, publish_response, "sin carreras asociadas")
    db_session.refresh(actividad)
    assert actividad.estado == ESTADO_BORRADOR


def test_publishing_finished_activity_redirects_to_edit_with_warning(
    admin_actividades_client, actividad_factory
):
    client, db_session, _, carrera = admin_actividades_client
    now = datetime.now()
    activity = actividad_factory(
        fecha_inicio=now - timedelta(days=2),
        estado=ESTADO_BORRADOR,
        carreras=[carrera],
    )

    response = client.post(f"/admin/actividades/{activity.id}/publicar")

    assert response.status_code == 303
    assert urlsplit(response.headers["location"]).path == (
        f"/admin/actividades/{activity.id}/editar"
    )
    assert_flash_redirect(client, response, (
        "La actividad ya finalizó, para publicar modificá las fechas de inicio y cierre"
    ))
    db_session.refresh(activity)
    assert activity.estado == ESTADO_BORRADOR


def test_disabling_activity_survey_releases_pending_credits(
    admin_actividades_client, user_factory
):
    client, db_session, docente, carrera = admin_actividades_client
    create_response = client.post(
        "/admin/actividades",
        data=actividad_form_data(docente.docente_id, carrera.id),
    )
    assert create_response.status_code == 303
    activity = db_session.query(Actividad).one()
    assert activity.encuesta_obligatoria is True

    student = user_factory()
    db_session.add(
        Asistencia(
            actividad_id=activity.id,
            user_id=student.id,
            estado_creditos=ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
        )
    )
    db_session.commit()
    update_data = actividad_form_data(
        docente.id, carrera.id, titulo=activity.titulo
    )
    update_data["encuesta_obligatoria"] = "false"

    response = client.post(f"/admin/actividades/{activity.id}", data=update_data)

    assert response.status_code == 303
    db_session.refresh(activity)
    attendance = db_session.query(Asistencia).one()
    assert activity.encuesta_obligatoria is False
    assert attendance.estado_creditos == ESTADO_CREDITOS_ACREDITADO
    assert accumulated_credits(db_session, student.id) == activity.creditos


def test_missing_activity_endpoints_redirect_with_not_found(admin_actividades_client):
    client, *_ = admin_actividades_client

    for path, method in [
        ("/admin/actividades/999/editar", client.get),
        ("/admin/actividades/999/preview", client.get),
        ("/admin/actividades/999/publicar", client.post),
        ("/admin/actividades/999/cancelar", client.post),
    ]:
        response = method(path)
        assert response.status_code == 303
        assert_flash_redirect(client, response, "Actividad no encontrada")

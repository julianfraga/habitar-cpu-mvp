import pytest
from datetime import datetime, timedelta, timezone

from app.models import (
    ESTADO_PUBLICADA,
    INSCRIPCION_ALTA,
    INSCRIPCION_BAJA,
    Inscripcion,
    Notification,
)
from app.config import settings
from app.services.credits import required_credits
from app.services.inscripcion import (
    EnrollError,
    active_enrollment,
    inscribir,
    inscriptos,
    my_actividades,
    inscriptos_dataframe,
    cancellation_penalty_applies,
    baja_penalizada_previa,
    revocar_penalizaciones_reprogramacion,
    unenroll,
)
from app.services.consultas_comunes import is_enrolled


def test_inscriptos_dataframe_incluye_identidad_y_asistencia(
    db_session, actividad_factory, user_factory
):
    activity = actividad_factory()
    student = user_factory(email="student@example.com")
    db_session.add(
        Inscripcion(
            actividad_id=activity.id,
            user_id=student.id,
            estado=INSCRIPCION_ALTA,
        )
    )
    db_session.commit()

    dataframe = inscriptos_dataframe(db_session, activity.id)

    assert dataframe.to_dict("records") == [
        {
            "apellido": student.apellido,
            "nombre": student.nombre,
            "email": student.email,
            "asistio": "no",
        }
    ]


def test_inscribir_y_consultar_inscripcion(db_session, actividad_factory, user_factory):
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=datetime.now(timezone.utc) + timedelta(days=2),
    )
    usuario = user_factory()

    resultado = inscribir(db_session, actividad.id, usuario.id)

    assert resultado.id == actividad.id
    assert is_enrolled(db_session, actividad.id, usuario.id)
    assert active_enrollment(db_session, actividad.id, usuario.id).estado == INSCRIPCION_ALTA
    assert [e.user_id for e in inscriptos(db_session, actividad.id)] == [usuario.id]


def test_inscripcion_cerrada_respeta_umbral_y_reprogramacion_corta(
    db_session, actividad_factory, user_factory
):
    now = datetime.now(timezone.utc)
    inicio = now + timedelta(hours=settings.CIERRE_INSCRIPCIONES_HORAS)
    inicio_reprogramada = now + timedelta(
        hours=max(settings.CIERRE_INSCRIPCIONES_HORAS / 2, 0.5)
    )
    cerrada = actividad_factory(
        estado=ESTADO_PUBLICADA, fecha_inicio=inicio
    )
    reprogramada = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=inicio_reprogramada,
    )
    reprogramada.reprogramada_corto_plazo = True
    db_session.commit()
    usuario = user_factory()

    assert cerrada.inscripcion_cerrada
    assert not reprogramada.inscripcion_cerrada
    assert inscribir(db_session, reprogramada.id, usuario.id) == reprogramada


def test_inscribir_rechaza_actividad_con_inscripcion_cerrada(
    db_session, actividad_factory, user_factory
):
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=datetime.now(timezone.utc)
        + timedelta(hours=settings.CIERRE_INSCRIPCIONES_HORAS),
    )
    usuario = user_factory()

    with pytest.raises(EnrollError, match="inscripción.*cerrada"):
        inscribir(db_session, actividad.id, usuario.id)


@pytest.mark.parametrize(
    "actividad_id, estado, mensaje",
    [(9999, None, "no existe"), (None, "borrador", "no está disponible")],
)
def test_inscribir_rechaza_actividad_invalida(
    db_session, actividad_factory, user_factory, actividad_id, estado, mensaje
):
    usuario = user_factory()
    if estado:
        actividad_id = actividad_factory(estado=estado).id

    with pytest.raises(EnrollError, match=mensaje):
        inscribir(db_session, actividad_id, usuario.id)


def test_inscribir_rechaza_duplicado_y_cupo_lleno(db_session, actividad_factory, user_factory):
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        cupo_max=1,
        fecha_inicio=datetime.now(timezone.utc) + timedelta(days=2),
    )
    primero = user_factory()
    segundo = user_factory()
    inscribir(db_session, actividad.id, primero.id)

    with pytest.raises(EnrollError, match="Ya estás inscripto"):
        inscribir(db_session, actividad.id, primero.id)
    with pytest.raises(EnrollError, match="No quedan cupos"):
        inscribir(db_session, actividad.id, segundo.id)


def test_unenroll_permite_reinscripcion(db_session, actividad_factory, user_factory):
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=datetime.now(timezone.utc) + timedelta(days=2),
    )
    usuario = user_factory()
    inscribir(db_session, actividad.id, usuario.id)

    unenroll(db_session, actividad.id, usuario.id)
    assert not is_enrolled(db_session, actividad.id, usuario.id)
    assert db_session.query(Inscripcion).filter_by(actividad_id=actividad.id).one().estado != INSCRIPCION_ALTA
    inscribir(db_session, actividad.id, usuario.id)
    assert is_enrolled(db_session, actividad.id, usuario.id)


@pytest.mark.parametrize(
    "hours_before, expected_penalty",
    [
        (settings.MARGEN_BAJA_HORAS * 2, False),
        (settings.MARGEN_BAJA_HORAS, False),
        (settings.MARGEN_BAJA_HORAS / 2, settings.MARGEN_BAJA_HORAS > 0),
    ],
)
def test_unenroll_penaliza_solo_dentro_del_margen_configurado(
    db_session, actividad_factory, user_factory, hours_before, expected_penalty
):
    now = datetime.now(timezone.utc)
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now + timedelta(hours=hours_before),
    )
    usuario = user_factory()
    db_session.add(
        Inscripcion(
            actividad_id=actividad.id,
            user_id=usuario.id,
            estado=INSCRIPCION_ALTA,
        )
    )
    db_session.commit()

    penalizada = unenroll(db_session, actividad.id, usuario.id, now=now)

    db_session.refresh(usuario.estudiante)
    db_session.refresh(db_session.query(Inscripcion).one())
    assert penalizada is expected_penalty
    assert db_session.query(Inscripcion).one().estado == INSCRIPCION_BAJA
    assert usuario.estudiante.creditos_penalizacion == (1.0 if expected_penalty else 0.0)
    assert required_credits(db_session, usuario.id) == (
        11.0 if expected_penalty else 10.0
    )
    notifications = db_session.query(Notification).filter_by(user_id=usuario.id).all()
    assert len(notifications) == (1 if expected_penalty else 0)
    if expected_penalty:
        assert "baja tardía" in notifications[0].mensaje
        assert (
            f"menos de {settings.MARGEN_BAJA_HORAS} horas"
            in notifications[0].mensaje
        )


@pytest.mark.parametrize(
    "hours_before_start, cancel, expected_penalty",
    [
        (
            settings.MARGEN_BAJA_HORAS
            + settings.CIERRE_INSCRIPCIONES_HORAS
            + 1,
            False,
            False,
        ),
        (
            settings.MARGEN_BAJA_HORAS
            + settings.CIERRE_INSCRIPCIONES_HORAS
            + 1,
            True,
            False,
        ),
        pytest.param(
            (settings.MARGEN_BAJA_HORAS + settings.CIERRE_INSCRIPCIONES_HORAS)
            / 2,
            True,
            True,
            marks=pytest.mark.skipif(
                settings.MARGEN_BAJA_HORAS
                <= settings.CIERRE_INSCRIPCIONES_HORAS,
                reason="No hay ventana configurable para inscribir y penalizar la baja.",
            ),
        ),
    ],
)
def test_inscripcion_y_baja_alrededor_del_margen_configurado(
    db_session,
    actividad_factory,
    user_factory,
    hours_before_start,
    cancel,
    expected_penalty,
):
    now = datetime.now(timezone.utc)
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now + timedelta(hours=hours_before_start),
    )
    usuario = user_factory()

    inscribir(db_session, actividad.id, usuario.id)
    penalizada = (
        unenroll(db_session, actividad.id, usuario.id, now=now)
        if cancel
        else False
    )

    assert penalizada is expected_penalty
    assert usuario.estudiante.creditos_penalizacion == (
        1.0 if expected_penalty else 0.0
    )
    enrollment = db_session.query(Inscripcion).one()
    assert enrollment.estado == (
        INSCRIPCION_BAJA if cancel else INSCRIPCION_ALTA
    )
    assert enrollment.baja_penalizada is expected_penalty


@pytest.mark.skipif(
    settings.UMBRAL_ANTICIPACION_REPROGRAMACION_DIAS * 24
    <= settings.CIERRE_INSCRIPCIONES_HORAS,
    reason="La actividad quedaría dentro del cierre al momento de inscripción.",
)
@pytest.mark.skipif(
    settings.MARGEN_BAJA_HORAS == 0,
    reason="Con margen de baja en 0 horas no existe baja tardía penalizable.",
)
@pytest.mark.parametrize(
    "days_before_start",
    [
        settings.UMBRAL_ANTICIPACION_REPROGRAMACION_DIAS,
        settings.UMBRAL_ANTICIPACION_REPROGRAMACION_DIAS + 1,
    ],
)
def test_actividad_creada_en_limite_y_un_dia_despues_mantiene_reglas_de_baja(
    db_session, actividad_factory, user_factory, days_before_start
):
    now = datetime.now(timezone.utc)
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now + timedelta(days=days_before_start),
    )
    usuario = user_factory()

    inscribir(db_session, actividad.id, usuario.id)
    momento_baja = actividad.fecha_inicio - timedelta(
        hours=settings.MARGEN_BAJA_HORAS / 2
    )
    penalizada = unenroll(
        db_session, actividad.id, usuario.id, now=momento_baja
    )

    db_session.refresh(usuario.estudiante)
    assert not actividad.reprogramada_corto_plazo
    assert penalizada
    assert usuario.estudiante.creditos_penalizacion == 1.0


def test_baja_penalizada_bloquea_reinscripcion_solo_en_esa_actividad(
    db_session, actividad_factory, user_factory
):
    now = datetime.now(timezone.utc)
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now + timedelta(hours=12),
    )
    otra_actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now + timedelta(days=2),
    )
    usuario = user_factory()
    inscribir(db_session, actividad.id, usuario.id)

    assert unenroll(db_session, actividad.id, usuario.id, now=now)
    assert baja_penalizada_previa(db_session, actividad, usuario.id)
    with pytest.raises(EnrollError, match="baja fue penalizada"):
        inscribir(db_session, actividad.id, usuario.id)
    assert inscribir(db_session, otra_actividad.id, usuario.id) == otra_actividad
    db_session.refresh(usuario.estudiante)
    assert usuario.estudiante.creditos_penalizacion == 1.0


def test_reprogramacion_revoca_penalizacion_y_baja_futura_no_penaliza(
    db_session, actividad_factory, user_factory
):
    now = datetime.now(timezone.utc)
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now + timedelta(hours=12),
    )
    usuario = user_factory()
    inscribir(db_session, actividad.id, usuario.id)
    assert unenroll(db_session, actividad.id, usuario.id, now=now)

    actividad.reprogramada_corto_plazo = True
    db_session.commit()
    assert revocar_penalizaciones_reprogramacion(db_session, actividad) == 1
    db_session.refresh(usuario.estudiante)
    db_session.refresh(db_session.query(Inscripcion).one())
    assert usuario.estudiante.creditos_penalizacion == 0.0
    assert not baja_penalizada_previa(db_session, actividad, usuario.id)

    inscribir(db_session, actividad.id, usuario.id)
    assert not unenroll(db_session, actividad.id, usuario.id, now=now)
    db_session.refresh(usuario.estudiante)
    assert usuario.estudiante.creditos_penalizacion == 0.0


def test_cancellation_penalty_applies_respeta_horas_y_estado(
    actividad_factory,
):
    now = datetime.now(timezone.utc)
    actividad_a_24_horas = actividad_factory(
        fecha_inicio=now + timedelta(hours=24)
    )
    actividad_a_23_horas = actividad_factory(
        fecha_inicio=now + timedelta(hours=23)
    )
    actividad_iniciada = actividad_factory(
        fecha_inicio=now - timedelta(minutes=1)
    )
    actividad_finalizada = actividad_factory(
        fecha_inicio=now - timedelta(hours=2)
    )
    actividad_finalizada.fecha_fin = now - timedelta(hours=1)

    assert not cancellation_penalty_applies(actividad_a_24_horas, now=now)
    assert cancellation_penalty_applies(actividad_a_23_horas, now=now)
    assert not cancellation_penalty_applies(actividad_iniciada, now=now)
    assert not cancellation_penalty_applies(actividad_finalizada, now=now)


def test_unenroll_no_penaliza_actividad_ya_iniciada(
    db_session, actividad_factory, user_factory
):
    now = datetime.now(timezone.utc)
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now - timedelta(minutes=30),
    )
    usuario = user_factory()
    db_session.add(
        Inscripcion(
            actividad_id=actividad.id,
            user_id=usuario.id,
            estado=INSCRIPCION_ALTA,
        )
    )
    db_session.commit()

    penalizada = unenroll(db_session, actividad.id, usuario.id, now=now)

    assert penalizada is False
    assert usuario.estudiante.creditos_penalizacion == 0.0
    assert db_session.query(Notification).filter_by(user_id=usuario.id).count() == 0


def test_unenroll_sin_inscripcion_falla(db_session, actividad_factory, user_factory):
    actividad = actividad_factory(estado=ESTADO_PUBLICADA)
    usuario = user_factory()

    with pytest.raises(EnrollError, match="No estás inscripto"):
        unenroll(db_session, actividad.id, usuario.id)


def test_unenroll_rechaza_actividad_finalizada(
    db_session, actividad_factory, user_factory
):
    now = datetime.now(timezone.utc)
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=now - timedelta(hours=4),
    )
    usuario = user_factory()
    db_session.add(
        Inscripcion(
            actividad_id=actividad.id,
            user_id=usuario.id,
            estado=INSCRIPCION_ALTA,
        )
    )
    db_session.commit()

    with pytest.raises(EnrollError, match="actividad ya finalizada"):
        unenroll(db_session, actividad.id, usuario.id)

    assert active_enrollment(db_session, actividad.id, usuario.id) is not None


def test_my_actividades_filtra_publicadas_y_ordena(db_session, actividad_factory, user_factory):
    usuario = user_factory()
    futura = actividad_factory(estado=ESTADO_PUBLICADA)
    borrador = actividad_factory(estado="borrador")
    futura.fecha_inicio = datetime.now(timezone.utc) + timedelta(days=2)
    inscribir(db_session, futura.id, usuario.id)
    db_session.add(
        Inscripcion(actividad_id=borrador.id, user_id=usuario.id, estado=INSCRIPCION_ALTA)
    )
    db_session.commit()

    assert my_actividades(db_session, usuario.id) == [futura]
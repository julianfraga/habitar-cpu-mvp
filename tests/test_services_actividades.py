from datetime import datetime, timedelta, timezone
from dataclasses import replace
from decimal import Decimal

import pytest

from app.models import (
    Docente,
    ESTADO_BORRADOR,
    ESTADO_CANCELADA,
    ESTADO_PUBLICADA,
    Inscripcion,
    Persona,
    RespuestaEncuesta,
)
from app.services.actividades import (
    ActividadContext,
    DocentesInput,
    clasificar_cambio_fecha,
    cancelar_y_republicar,
    create,
    cupo_info,
    get,
    inscriptos_count,
    list_all,
    listar_disponibles,
    resolver_docentes,
    update,
    update_estado,
)


def test_get_devuelve_actividad_o_none(db_session, actividad_factory):
    actividad = actividad_factory()

    assert get(db_session, actividad.id) == actividad
    assert get(db_session, 9999) is None


def test_inscriptos_count_y_cupo_info_cuentan_solo_inscripciones_activas(
    db_session, actividad_factory, user_factory
):
    actividad = actividad_factory(cupo_max=2)
    activos = [user_factory(), user_factory()]
    db_session.add_all(
        [
            Inscripcion(actividad_id=actividad.id, user_id=activos[0].id, estado="inscripto"),
            Inscripcion(actividad_id=actividad.id, user_id=activos[1].id, estado="baja"),
        ]
    )
    db_session.commit()

    assert inscriptos_count(db_session, actividad.id) == 1
    assert cupo_info(db_session, actividad) == {"taken": 1, "free": 1, "full": False}


def test_cupo_info_no_informa_cupos_negativos(db_session, actividad_factory, user_factory):
    actividad = actividad_factory(cupo_max=1)
    usuario = user_factory()
    db_session.add(Inscripcion(actividad_id=actividad.id, user_id=usuario.id))
    db_session.commit()

    assert cupo_info(db_session, actividad) == {"taken": 1, "free": 0, "full": True}


def test_listar_disponibles_aplica_filtros_y_ordena(db_session, actividad_factory, carrera_factory):
    carrera = carrera_factory()
    base = datetime.now(timezone.utc) + timedelta(days=10)
    actividad_factory(
        titulo="Taller virtual",
        fecha_inicio=base + timedelta(hours=2),
        estado=ESTADO_PUBLICADA,
        tipo="virtual",
        creditos=4,
        carreras=[carrera],
    )
    esperada = actividad_factory(
        titulo="Taller presencial",
        fecha_inicio=base,
        estado=ESTADO_PUBLICADA,
        tipo="presencial",
        creditos=3,
        carreras=[carrera],
    )
    actividad_factory(titulo="Borrador", fecha_inicio=base, carreras=[carrera])

    resultado = listar_disponibles(
        db_session,
        carrera_id=[carrera.id],
        tipo="presencial",
        fecha=base.date().isoformat(),
        min_creditos=3,
    )

    assert resultado == [esperada]


def test_clasificar_cambio_fecha_aplica_limites_inclusivos(
    actividad_factory,
):
    now = datetime.now(timezone.utc)
    con_anticipacion = actividad_factory(
        fecha_inicio=now + timedelta(days=10)
    )
    sin_anticipacion = actividad_factory(
        fecha_inicio=now + timedelta(days=4)
    )

    assert clasificar_cambio_fecha(
        con_anticipacion,
        con_anticipacion.fecha_inicio + timedelta(days=1),
        fecha_modificacion=now,
    ) == "edicion_estandar"
    assert clasificar_cambio_fecha(
        sin_anticipacion,
        sin_anticipacion.fecha_inicio + timedelta(hours=48),
        fecha_modificacion=now,
    ) == "cancelar_republicar"
    assert clasificar_cambio_fecha(
        sin_anticipacion,
        sin_anticipacion.fecha_inicio + timedelta(hours=47, minutes=59),
        fecha_modificacion=now,
    ) == "reprogramacion"


def test_cancelar_y_republicar_crea_actividad_nueva_sin_traspasar_inscriptos(
    db_session, actividad_factory, user_factory, carrera_factory
):
    carrera = carrera_factory()
    actividad = actividad_factory(
        estado=ESTADO_PUBLICADA,
        fecha_inicio=datetime.now(timezone.utc) + timedelta(days=2),
        carreras=[carrera],
    )
    estudiante = user_factory()
    db_session.add(
        Inscripcion(
            actividad_id=actividad.id,
            user_id=estudiante.id,
            estado="inscripto",
        )
    )
    db_session.commit()
    contexto = ActividadContext(
        titulo="Nueva fecha",
        descripcion=actividad.descripcion,
        tipo=actividad.tipo,
        fecha_inicio=actividad.fecha_inicio + timedelta(days=3),
        fecha_fin=actividad.fecha_fin + timedelta(days=3),
        lugar=actividad.lugar,
        docentes=list(actividad.docentes),
        creditos=Decimal(str(actividad.creditos)),
        cupo_max=actividad.cupo_max,
        encuesta_obligatoria=actividad.encuesta_obligatoria,
        preguntas=actividad.preguntas,
        carreras_asociadas=list(actividad.carreras_asociadas),
    )

    nueva, inscriptos_anteriores = cancelar_y_republicar(
        db_session, actividad, contexto, created_by=None
    )

    assert actividad.estado == ESTADO_CANCELADA
    assert nueva.id != actividad.id
    assert nueva.estado == ESTADO_PUBLICADA
    assert not nueva.inscripciones
    assert inscriptos_anteriores[0].estado == "baja"
    assert not inscriptos_anteriores[0].baja_penalizada


def test_listar_disponibles_devuelve_vacio_para_estudiante_sin_carreras(db_session):
    assert listar_disponibles(db_session, carrera_id=[]) == []


def test_listar_disponibles_solo_con_cupo_excluye_llenas(
    db_session, actividad_factory, user_factory
):
    actividad = actividad_factory(estado=ESTADO_PUBLICADA, cupo_max=1)
    usuario = user_factory()
    db_session.add(Inscripcion(actividad_id=actividad.id, user_id=usuario.id))
    db_session.commit()

    assert listar_disponibles(db_session, solo_con_cupo=True) == []


def test_list_all_filtra_carreras_y_acepta_todas(db_session, actividad_factory, carrera_factory):
    arquitectura = carrera_factory()
    diseno = carrera_factory(nombre="Diseño")
    con_carrera = actividad_factory(carreras=[arquitectura])
    sin_carrera = actividad_factory(carreras=[diseno])

    assert list_all(db_session, carreras_ids=[str(arquitectura.id)]) == [con_carrera]
    assert {a.id for a in list_all(db_session, carreras_ids=["todas"])} == {
        con_carrera.id,
        sin_carrera.id,
    }


def test_list_all_ordering_uses_defaults_and_stable_tiebreakers(
    db_session, actividad_factory
):
    base = datetime(2030, 10, 10, tzinfo=timezone.utc)
    alpha = actividad_factory(
        titulo="Alfa", fecha_inicio=base, estado=ESTADO_PUBLICADA, cupo_max=3
    )
    beta = actividad_factory(
        titulo="Beta", fecha_inicio=base + timedelta(days=1), estado=ESTADO_BORRADOR,
        cupo_max=12,
    )
    beta_publicada = actividad_factory(
        titulo="Beta", fecha_inicio=base + timedelta(days=1), estado=ESTADO_PUBLICADA,
        cupo_max=5,
    )

    assert list_all(db_session, orden="nombre") == [alpha, beta_publicada, beta]
    assert list_all(db_session, orden="fecha") == [beta_publicada, beta, alpha]
    assert list_all(db_session, orden="cupo") == [beta_publicada, alpha, beta]
    assert list_all(db_session, orden="cupo", direccion="asc") == [
        alpha, beta_publicada, beta
    ]
    assert list_all(db_session, orden="estado") == [beta_publicada, alpha, beta]
    assert list_all(db_session, orden="nombre", direccion="desc") == [
        beta_publicada, beta, alpha
    ]


def test_list_all_state_ordering_uses_derived_finalized_status(
    db_session, actividad_factory
):
    now = datetime.now(timezone.utc)
    publicada = actividad_factory(
        titulo="Publicada",
        fecha_inicio=now + timedelta(days=2),
        estado=ESTADO_PUBLICADA,
    )
    publicada_mas_reciente = actividad_factory(
        titulo="Publicada más reciente",
        fecha_inicio=now + timedelta(days=5),
        estado=ESTADO_PUBLICADA,
    )
    finalizada = actividad_factory(
        titulo="Finalizada",
        fecha_inicio=now - timedelta(days=2),
        estado=ESTADO_PUBLICADA,
    )
    cancelada = actividad_factory(
        titulo="Cancelada",
        fecha_inicio=now + timedelta(days=1),
        estado=ESTADO_CANCELADA,
    )
    vencida = actividad_factory(
        titulo="Vencida",
        fecha_inicio=now - timedelta(days=1),
        estado=ESTADO_BORRADOR,
    )

    assert list_all(db_session, orden="estado") == [
        publicada_mas_reciente,
        publicada,
        finalizada,
        cancelada,
        vencida,
    ]


def test_create_y_update_persisten_actividad(db_session):
    contexto = ActividadContext(
        titulo="Nueva actividad",
        descripcion="",
        tipo="presencial",
        fecha_inicio=datetime(2026, 10, 1),
        fecha_fin=datetime(2026, 10, 1, 2),
        lugar="",
        docentes=[],
        creditos=Decimal("1"),
        cupo_max=30,
        encuesta_obligatoria=True,
        preguntas={"q1": "¿Qué te pareció la actividad?"},
        carreras_asociadas=[],
    )
    actividad = create(
        db_session,
        contexto,
    )
    contexto_actualizado = replace(
        contexto,
        titulo="Actividad actualizada",
        creditos=Decimal("5"),
    )
    update(db_session, actividad, contexto_actualizado)

    assert get(db_session, actividad.id).titulo == "Actividad actualizada"
    assert get(db_session, actividad.id).creditos == 5
    assert get(db_session, actividad.id).estado == ESTADO_BORRADOR


def test_update_rejects_changing_survey_questions_after_response(
    db_session, actividad_factory, user_factory
):
    actividad = actividad_factory()
    estudiante = user_factory()
    db_session.add(
        RespuestaEncuesta(
            actividad_id=actividad.id,
            estudiante_id=estudiante.id,
            respuestas={"q1": "Respuesta"},
            rating=5,
        )
    )
    db_session.commit()
    contexto = ActividadContext(
        titulo=actividad.titulo,
        descripcion=actividad.descripcion,
        tipo=actividad.tipo,
        fecha_inicio=actividad.fecha_inicio,
        fecha_fin=actividad.fecha_fin,
        lugar=actividad.lugar,
        docentes=[],
        creditos=Decimal(str(actividad.creditos)),
        cupo_max=actividad.cupo_max,
        encuesta_obligatoria=actividad.encuesta_obligatoria,
        preguntas={"q1": "Pregunta modificada"},
        carreras_asociadas=[],
    )

    with pytest.raises(ValueError, match="después de recibir respuestas"):
        update(db_session, actividad, contexto)


def test_update_estado_actualiza_estado_sin_requerir_contexto(
    db_session, actividad_factory
):
    actividad = actividad_factory()

    update_estado(db_session, actividad, ESTADO_PUBLICADA)

    assert get(db_session, actividad.id).estado == ESTADO_PUBLICADA


def test_resolver_docentes_asigna_email_a_persona_existente_sin_email(db_session):
    persona = Persona(nombre="Eva", apellido="Invitada")
    docente = Docente(persona=persona)
    db_session.add(docente)
    db_session.commit()

    resultado = resolver_docentes(
        db_session,
        DocentesInput(
            ids=[],
            nombres=[" Eva "],
            apellidos=["Invitada"],
            emails=[" EVA@Example.com "],
        ),
    )

    assert resultado == [docente]
    assert persona.email == "eva@example.com"


def test_resolver_docentes_creates_and_links_persona_for_new_docente(db_session):
    resultado = resolver_docentes(
        db_session,
        DocentesInput(
            ids=[],
            nombres=["Eva"],
            apellidos=["Invitada"],
            emails=["eva@example.com"],
        ),
    )
    db_session.flush()

    assert len(resultado) == 1
    assert resultado[0].persona.nombre == "Eva"
    assert resultado[0].persona.apellido == "Invitada"
    assert resultado[0].persona.email == "eva@example.com"
    assert resultado[0].persona.docente is resultado[0]


def test_resolver_docentes_rechaza_email_asociado_a_otro_nombre(db_session):
    db_session.add(
        Persona(
            nombre="Ana",
            apellido="Persona",
            email="ana@example.com",
        )
    )
    db_session.commit()

    with pytest.raises(ValueError, match="asociado a otra persona"):
        resolver_docentes(
            db_session,
            DocentesInput(
                ids=[],
                nombres=["Eva"],
                apellidos=["Invitada"],
                emails=["ana@example.com"],
            ),
        )


def test_resolver_docentes_rechaza_email_nuevo_para_nombre_ya_vinculado(db_session):
    docente = Docente(
        persona=Persona(
            nombre="Eva",
            apellido="Invitada",
            email="eva-anterior@example.com",
        )
    )
    db_session.add(docente)
    db_session.commit()

    with pytest.raises(ValueError, match="otro email asociado"):
        resolver_docentes(
            db_session,
            DocentesInput(
                ids=[],
                nombres=["Eva"],
                apellidos=["Invitada"],
                emails=["eva-nuevo@example.com"],
            ),
        )
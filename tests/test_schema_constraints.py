from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Estudiante, RespuestaEncuesta


@pytest.mark.parametrize("rating", [0, 6])
def test_survey_rating_database_constraint_rejects_out_of_range_values(
    db_session, actividad_factory, user_factory, rating
):
    activity = actividad_factory()
    student = user_factory()
    response = RespuestaEncuesta(
        actividad_id=activity.id,
        estudiante_id=student.id,
        respuestas={},
        rating=rating,
    )
    db_session.add(response)

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("cupo_max", 0),
        ("tipo", "desconocido"),
        ("estado", "finalizada"),
    ],
)
def test_activity_checks_reject_invalid_values(
    db_session, actividad_factory, attribute, value
):
    activity = actividad_factory()
    setattr(activity, attribute, value)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_activity_check_rejects_end_before_start(db_session, actividad_factory):
    activity = actividad_factory()
    activity.fecha_fin = activity.fecha_inicio - timedelta(days=1)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_career_check_rejects_nonpositive_required_credits(
    db_session, carrera_factory
):
    career = carrera_factory()
    career.creditos_requeridos = 0

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_student_credit_check_rejects_values_not_in_half_credit_steps(
    db_session, user_factory
):
    student = user_factory()
    student.estudiante.creditos_requeridos = Decimal("1.2")

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_student_credit_balances_preserve_half_credit_exactly(
    db_session, user_factory
):
    student = user_factory()
    student.estudiante.creditos_acreditados = Decimal("0.5")
    student.estudiante.creditos_requeridos = Decimal("10.5")
    student.estudiante.creditos_penalizacion = Decimal("1.5")
    student_id = student.id
    db_session.commit()
    db_session.expire_all()

    refreshed = db_session.get(Estudiante, student_id)

    assert refreshed is not None
    assert refreshed.creditos_acreditados == Decimal("0.5")
    assert refreshed.creditos_requeridos == Decimal("10.5")
    assert refreshed.creditos_penalizacion == Decimal("1.5")

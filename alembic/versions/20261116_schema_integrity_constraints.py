"""Add checks for closed domains and valid numeric/date ranges."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_schema_integrity_checks"
down_revision: Union[str, Sequence[str], None] = "20261116_survey_rating_range"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINTS = (
    (
        "actividades",
        "ck_actividades_fecha_fin_no_anterior",
        "fecha_fin >= fecha_inicio",
    ),
    ("actividades", "ck_actividades_cupo_positivo", "cupo_max > 0"),
    (
        "actividades",
        "ck_actividades_tipo_valido",
        "tipo IN ('presencial', 'virtual')",
    ),
    (
        "actividades",
        "ck_actividades_estado_valido",
        "estado IN ('borrador', 'publicada', 'cancelada')",
    ),
    (
        "carreras",
        "ck_carreras_creditos_requeridos_positivo",
        "creditos_requeridos > 0",
    ),
    (
        "users",
        "ck_users_rol_valido",
        "rol IN ('estudiante', 'coordinacion', 'docente', 'director')",
    ),
    (
        "inscripciones",
        "ck_inscripciones_estado_valido",
        "estado IN ('inscripto', 'baja')",
    ),
    (
        "asistencia",
        "ck_asistencia_estado_creditos_valido",
        "estado_creditos IN ('acreditado', 'pendiente_encuesta')",
    ),
    (
        "password_resets",
        "ck_password_resets_attempts_nonnegative",
        "attempts >= 0",
    ),
)


def upgrade() -> None:
    for table, name, condition in CONSTRAINTS:
        op.create_check_constraint(name, table, condition)


def downgrade() -> None:
    for table, name, _condition in reversed(CONSTRAINTS):
        op.drop_constraint(name, table, type_="check")

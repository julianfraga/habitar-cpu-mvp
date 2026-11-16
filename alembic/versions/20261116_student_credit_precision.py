"""Use exact decimal storage for credit amounts in half-credit increments."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261116_credits_numeric"
down_revision: Union[str, Sequence[str], None] = "20261116_drop_session_creator"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CREDIT_COLUMNS = (
    "creditos_acreditados",
    "creditos_requeridos",
    "creditos_penalizacion",
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM estudiantes
                WHERE ABS(creditos_acreditados::numeric * 2
                          - ROUND(creditos_acreditados::numeric * 2)) > 0.000002
                   OR ABS(creditos_requeridos::numeric * 2
                          - ROUND(creditos_requeridos::numeric * 2)) > 0.000002
                   OR ABS(creditos_penalizacion::numeric * 2
                          - ROUND(creditos_penalizacion::numeric * 2)) > 0.000002
            ) THEN
                RAISE EXCEPTION
                    'Student credit values must be multiples of 0.5 before conversion';
            END IF;
        END
        $$;
        """
    )
    for column in CREDIT_COLUMNS:
        op.alter_column(
            "estudiantes",
            column,
            existing_type=sa.Float(),
            type_=sa.Numeric(8, 1),
            postgresql_using=f"{column}::numeric(8, 1)",
        )
    for name, column in (
        ("ck_estudiante_creditos_acreditados_medio", "creditos_acreditados"),
        ("ck_estudiante_creditos_requeridos_medio", "creditos_requeridos"),
        ("ck_estudiante_creditos_penalizacion_medio", "creditos_penalizacion"),
    ):
        op.create_check_constraint(
            name,
            "estudiantes",
            f"{column} * 2 = CAST({column} * 2 AS INTEGER)",
        )


def downgrade() -> None:
    for name in (
        "ck_estudiante_creditos_penalizacion_medio",
        "ck_estudiante_creditos_requeridos_medio",
        "ck_estudiante_creditos_acreditados_medio",
    ):
        op.drop_constraint(name, "estudiantes", type_="check")
    for column in reversed(CREDIT_COLUMNS):
        op.alter_column(
            "estudiantes",
            column,
            existing_type=sa.Numeric(8, 1),
            type_=sa.Float(),
            postgresql_using=f"{column}::double precision",
        )

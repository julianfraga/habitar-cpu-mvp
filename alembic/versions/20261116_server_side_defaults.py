"""Add database-side defaults matching ORM insert defaults."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261116_server_defaults"
down_revision: Union[str, Sequence[str], None] = "20261116_restrict_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULTS = (
    ("actividades", "descripcion", sa.Text(), sa.text("''")),
    ("actividades", "tipo", sa.String(length=20), sa.text("'presencial'")),
    ("actividades", "lugar", sa.String(length=200), sa.text("''")),
    ("actividades", "creditos", sa.Numeric(precision=8, scale=1), sa.text("1.0")),
    ("actividades", "preguntas", sa.JSON(), sa.text("'{}'")),
    ("actividades", "cupo_max", sa.Integer(), sa.text("30")),
    ("actividades", "estado", sa.String(length=20), sa.text("'borrador'")),
    ("users", "rol", sa.String(length=20), sa.text("'estudiante'")),
    ("inscripciones", "estado", sa.String(length=20), sa.text("'inscripto'")),
    ("inscripciones", "reminded", sa.Boolean(), sa.text("false")),
    ("notifications", "leido", sa.Boolean(), sa.text("false")),
)


def upgrade() -> None:
    for table, column, column_type, default in DEFAULTS:
        op.alter_column(
            table,
            column,
            existing_type=column_type,
            existing_nullable=False,
            server_default=default,
        )


def downgrade() -> None:
    for table, column, column_type, _default in reversed(DEFAULTS):
        op.alter_column(
            table,
            column,
            existing_type=column_type,
            existing_nullable=False,
            server_default=None,
        )

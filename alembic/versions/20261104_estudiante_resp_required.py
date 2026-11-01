"""Require a student for every survey response."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261104_estudiante_resp"
down_revision: Union[str, Sequence[str], None] = "20261103_encuestas_json"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "respuestas_encuesta" not in inspector.get_table_names():
        return

    column = next(
        (
            item
            for item in inspector.get_columns("respuestas_encuesta")
            if item["name"] == "estudiante_id"
        ),
        None,
    )
    if column is None:
        raise RuntimeError(
            "Cannot require survey respondent: estudiante_id column is missing."
        )
    if bind.scalar(
        sa.text(
            "SELECT COUNT(*) FROM respuestas_encuesta "
            "WHERE estudiante_id IS NULL"
        )
    ):
        raise RuntimeError(
            "Cannot require survey respondent: some responses have no student."
        )
    if column["nullable"]:
        with op.batch_alter_table("respuestas_encuesta") as batch_op:
            batch_op.alter_column(
                "estudiante_id",
                existing_type=column["type"],
                nullable=False,
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "respuestas_encuesta" not in inspector.get_table_names():
        return
    column = next(
        (
            item
            for item in inspector.get_columns("respuestas_encuesta")
            if item["name"] == "estudiante_id"
        ),
        None,
    )
    if column is not None and not column["nullable"]:
        with op.batch_alter_table("respuestas_encuesta") as batch_op:
            batch_op.alter_column(
                "estudiante_id",
                existing_type=column["type"],
                nullable=True,
            )

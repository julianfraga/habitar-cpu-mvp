"""Rename the legacy survey activity index to match the ORM model."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261106_fix_survey_idx"
down_revision: Union[str, Sequence[str], None] = "20261105_drop_act_docente"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "respuestas_encuesta"
LEGACY_INDEX = "ix_survey_responses_actividad_id"
MODEL_INDEX = "ix_respuestas_encuesta_actividad_id"


def _set_activity_index(source: str, target: str) -> None:
    inspector = sa.inspect(op.get_bind())
    if TABLE_NAME not in inspector.get_table_names():
        return

    indexes = {
        index["name"] for index in inspector.get_indexes(TABLE_NAME)
    }
    if source in indexes and target in indexes:
        op.drop_index(source, table_name=TABLE_NAME)
    elif source in indexes:
        op.drop_index(source, table_name=TABLE_NAME)
        op.create_index(target, TABLE_NAME, ["actividad_id"])
    elif target not in indexes:
        op.create_index(target, TABLE_NAME, ["actividad_id"])


def upgrade() -> None:
    _set_activity_index(LEGACY_INDEX, MODEL_INDEX)


def downgrade() -> None:
    _set_activity_index(MODEL_INDEX, LEGACY_INDEX)

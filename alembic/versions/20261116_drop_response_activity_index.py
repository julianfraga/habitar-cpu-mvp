"""Drop activity index covered by the unique response index prefix."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_drop_response_idx"
down_revision: Union[str, Sequence[str], None] = "20261116_schema_integrity_checks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        "ix_respuestas_encuesta_actividad_id",
        table_name="respuestas_encuesta",
    )


def downgrade() -> None:
    op.create_index(
        "ix_respuestas_encuesta_actividad_id",
        "respuestas_encuesta",
        ["actividad_id"],
    )

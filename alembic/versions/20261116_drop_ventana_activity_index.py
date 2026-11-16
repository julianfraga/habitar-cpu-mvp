"""Drop activity index duplicated by the unique constraint."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_drop_ventana_idx"
down_revision: Union[str, Sequence[str], None] = "20261116_drop_response_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        "ix_ventanas_asistencia_actividad_id",
        table_name="ventanas_asistencia",
    )


def downgrade() -> None:
    op.create_index(
        "ix_ventanas_asistencia_actividad_id",
        "ventanas_asistencia",
        ["actividad_id"],
    )

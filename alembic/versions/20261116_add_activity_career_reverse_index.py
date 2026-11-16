"""Index career-side lookups in the activity-career association."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_activity_career_idx"
down_revision: Union[str, Sequence[str], None] = "20261116_drop_docente_pk_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_actividad_carrera_carrera_id",
        "actividad_carrera",
        ["carrera_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_actividad_carrera_carrera_id",
        table_name="actividad_carrera",
    )

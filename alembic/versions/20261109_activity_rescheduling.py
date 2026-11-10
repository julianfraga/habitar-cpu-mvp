"""Track activity rescheduling and penalized cancellations."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261109_activity_rescheduling"
down_revision: Union[str, Sequence[str], None] = "20261106_fix_survey_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "actividades",
        sa.Column(
            "reprogramada_corto_plazo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "inscripciones",
        sa.Column(
            "baja_penalizada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("inscripciones", "baja_penalizada")
    op.drop_column("actividades", "reprogramada_corto_plazo")

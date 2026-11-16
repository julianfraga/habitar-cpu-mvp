"""Constrain survey ratings to the supported 1-5 range."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_survey_rating_range"
down_revision: Union[str, Sequence[str], None] = "20261116_attendance_validator"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_respuestas_encuesta_rating_range",
        "respuestas_encuesta",
        "rating BETWEEN 1 AND 5",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_respuestas_encuesta_rating_range",
        "respuestas_encuesta",
        type_="check",
    )

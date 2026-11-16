"""Require an actor for every attendance validation."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261116_attendance_validator"
down_revision: Union[str, Sequence[str], None] = "20261116_server_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE asistencia SET validated_by = user_id "
            "WHERE validated_by IS NULL"
        )
    )
    op.alter_column(
        "asistencia",
        "validated_by",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "asistencia",
        "validated_by",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )

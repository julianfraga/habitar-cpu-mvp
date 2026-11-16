"""Require creation timestamps on personas."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261116_persona_created_at"
down_revision: Union[str, Sequence[str], None] = "20261116_expand_text_lengths"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM personas WHERE created_at IS NULL
            ) THEN
                RAISE EXCEPTION
                    'Personas with NULL created_at must be reviewed before migration';
            END IF;
        END
        $$;
        """
    )
    op.alter_column(
        "personas",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "personas",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=True,
    )

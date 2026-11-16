"""Remove unused creator reference from attendance sessions."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261116_drop_session_creator"
down_revision: Union[str, Sequence[str], None] = "20261116_msg_reads_user_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("sesiones_asistencia", "created_by")


def downgrade() -> None:
    op.add_column(
        "sesiones_asistencia",
        sa.Column("created_by", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "sesiones_asistencia_created_by_fkey",
        "sesiones_asistencia",
        "users",
        ["created_by"],
        ["id"],
    )

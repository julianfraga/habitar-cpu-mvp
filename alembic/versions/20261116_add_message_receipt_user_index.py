"""Index message receipts by user for unread lookups."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_msg_reads_user_idx"
down_revision: Union[str, Sequence[str], None] = "20261116_activity_career_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_mensaje_lecturas_user_id",
        "mensaje_lecturas",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mensaje_lecturas_user_id",
        table_name="mensaje_lecturas",
    )

"""Drop duplicate index on the personas primary key."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_drop_persona_pk_index"
down_revision: Union[str, Sequence[str], None] = "20261116_drop_ventana_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_personas_id", table_name="personas")


def downgrade() -> None:
    op.create_index("ix_personas_id", "personas", ["id"])

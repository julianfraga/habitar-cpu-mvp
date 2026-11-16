"""Drop duplicate index on the docentes primary key."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_drop_docente_pk_index"
down_revision: Union[str, Sequence[str], None] = "20261116_drop_persona_pk_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_docentes_id", table_name="docentes")


def downgrade() -> None:
    op.create_index("ix_docentes_id", "docentes", ["id"])

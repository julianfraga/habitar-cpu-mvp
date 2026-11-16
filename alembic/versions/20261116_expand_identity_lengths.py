"""Expand email and career-name fields to accommodate valid values."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261116_expand_text_lengths"
down_revision: Union[str, Sequence[str], None] = "20261116_credits_numeric"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "personas",
        "email",
        existing_type=sa.String(length=120),
        type_=sa.String(length=254),
        existing_nullable=True,
        postgresql_using="email::varchar(254)",
    )
    op.alter_column(
        "carreras",
        "nombre",
        existing_type=sa.String(length=50),
        type_=sa.String(length=120),
        existing_nullable=False,
        postgresql_using="nombre::varchar(120)",
    )


def downgrade() -> None:
    op.alter_column(
        "carreras",
        "nombre",
        existing_type=sa.String(length=120),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="nombre::varchar(50)",
    )
    op.alter_column(
        "personas",
        "email",
        existing_type=sa.String(length=254),
        type_=sa.String(length=120),
        existing_nullable=True,
        postgresql_using="email::varchar(120)",
    )

"""Drop legacy actividades.docente_id."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261105_drop_act_docente"
down_revision: Union[str, Sequence[str], None] = "20261104_estudiante_resp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "actividades" not in inspector.get_table_names():
        return

    columns = {
        column["name"]: column
        for column in inspector.get_columns("actividades")
    }
    if "docente_id" not in columns:
        return

    foreign_keys = inspector.get_foreign_keys("actividades")
    legacy_fk = next(
        (
            foreign_key
            for foreign_key in foreign_keys
            if foreign_key.get("constrained_columns") == ["docente_id"]
        ),
        None,
    )
    with op.batch_alter_table(
        "actividades",
        naming_convention={
            "fk": "%(table_name)s_%(column_0_name)s_fkey",
        },
    ) as batch_op:
        if legacy_fk is not None:
            batch_op.drop_constraint(
                legacy_fk.get("name") or "actividades_docente_id_fkey",
                type_="foreignkey",
            )
        batch_op.drop_column("docente_id")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "actividades" not in tables:
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("actividades")
    }
    if "docente_id" in columns:
        return

    with op.batch_alter_table("actividades") as batch_op:
        batch_op.add_column(
            sa.Column(
                "docente_id",
                sa.Integer(),
                sa.ForeignKey(
                    "users.id",
                    name="actividades_docente_id_fkey",
                ),
                nullable=True,
            )
        )

    if {"actividad_docente", "docentes", "personas", "users"} <= tables:
        op.execute(
            sa.text(
                """
                UPDATE actividades
                SET docente_id = (
                    SELECT MIN(u.id)
                    FROM actividad_docente ad
                    JOIN docentes d ON d.id = ad.docente_id
                    JOIN personas p ON p.id = d.persona_id
                    JOIN users u ON u.persona_id = p.id
                    WHERE ad.actividad_id = actividades.id
                    HAVING COUNT(DISTINCT u.id) = 1
                )
                """
            )
        )

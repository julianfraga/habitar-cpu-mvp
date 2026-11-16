"""Restrict physical deletion of identities and activities with retained history."""
from typing import Sequence, Union

from alembic import op


revision: str = "20261116_restrict_history"
down_revision: Union[str, Sequence[str], None] = "20261109_activity_rescheduling"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FOREIGN_KEYS = (
    (
        "fk_users_persona_id",
        "users",
        "personas",
        "persona_id",
        "id",
        "CASCADE",
        None,
    ),
    (
        "fk_docentes_persona",
        "docentes",
        "personas",
        "persona_id",
        "id",
        "CASCADE",
        None,
    ),
    (
        "estudiantes_user_id_fkey",
        "estudiantes",
        "users",
        "user_id",
        "id",
        "CASCADE",
        "RESTRICT",
    ),
    (
        "fk_respuestas_encuesta_estudiante",
        "respuestas_encuesta",
        "estudiantes",
        "estudiante_id",
        "user_id",
        "CASCADE",
        "RESTRICT",
    ),
    (
        "survey_responses_actividad_id_fkey",
        "respuestas_encuesta",
        "actividades",
        "actividad_id",
        "id",
        None,
        "RESTRICT",
    ),
    (
        "inscripciones_actividad_id_fkey",
        "inscripciones",
        "actividades",
        "actividad_id",
        "id",
        None,
        "RESTRICT",
    ),
    (
        "mensajes_remitente_id_fkey",
        "mensajes",
        "users",
        "remitente_id",
        "id",
        "CASCADE",
        "RESTRICT",
    ),
    (
        "mensajes_destinatario_id_fkey",
        "mensajes",
        "users",
        "destinatario_id",
        "id",
        "CASCADE",
        "RESTRICT",
    ),
)


def _replace_foreign_keys(*, restore: bool = False) -> None:
    for (
        name,
        table,
        referred_table,
        local_column,
        referred_column,
        old_action,
        new_action,
    ) in FOREIGN_KEYS:
        op.drop_constraint(name, table, type_="foreignkey")
        ondelete = old_action if restore else new_action
        kwargs = {"ondelete": ondelete} if ondelete else {}
        op.create_foreign_key(
            name,
            table,
            referred_table,
            [local_column],
            [referred_column],
            **kwargs,
        )


def upgrade() -> None:
    _replace_foreign_keys()


def downgrade() -> None:
    _replace_foreign_keys(restore=True)

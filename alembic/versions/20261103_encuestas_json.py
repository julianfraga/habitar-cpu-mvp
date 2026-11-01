"""Store activity survey questions and student answers as JSON."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261103_encuestas_json"
down_revision: Union[str, Sequence[str], None] = "20261102_docentes_persona"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(bind: sa.Connection, table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(bind).get_columns(table_name)
    }


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "actividades" in tables:
        activity_columns = _column_names(bind, "actividades")
        if "preguntas" not in activity_columns:
            op.add_column(
                "actividades",
                sa.Column("preguntas", sa.JSON(), nullable=True),
            )
            activities = sa.Table(
                "actividades", sa.MetaData(), autoload_with=bind
            )
            for actividad_id, encuesta_obligatoria in bind.execute(
                sa.select(
                    activities.c.id,
                    activities.c.encuesta_obligatoria,
                )
            ):
                preguntas = (
                    {"q1": "¿Qué te pareció la actividad?"}
                    if encuesta_obligatoria
                    else {}
                )
                bind.execute(
                    sa.update(activities)
                    .where(activities.c.id == actividad_id)
                    .values(preguntas=preguntas)
                )
            with op.batch_alter_table("actividades") as batch_op:
                batch_op.alter_column(
                    "preguntas",
                    existing_type=sa.JSON(),
                    nullable=False,
                )

    if "survey_responses" not in tables:
        return
    if "respuestas_encuesta" in tables:
        raise RuntimeError(
            "Cannot rename survey_responses: respuestas_encuesta already exists."
        )
    if "estudiantes" not in tables:
        raise RuntimeError(
            "Cannot link survey responses: estudiantes table does not exist."
        )

    responses = sa.Table(
        "survey_responses", sa.MetaData(), autoload_with=bind
    )
    students = sa.Table("estudiantes", sa.MetaData(), autoload_with=bind)
    missing_students = bind.scalar(
        sa.select(sa.func.count())
        .select_from(
            responses.outerjoin(
                students, responses.c.user_id == students.c.user_id
            )
        )
        .where(students.c.user_id.is_(None))
    )
    if missing_students:
        raise RuntimeError(
            "Cannot migrate survey responses: some respondents are not students."
        )

    op.rename_table("survey_responses", "respuestas_encuesta")
    responses = sa.Table(
        "respuestas_encuesta", sa.MetaData(), autoload_with=bind
    )
    response_columns = _column_names(bind, "respuestas_encuesta")
    if "respuestas" not in response_columns:
        op.add_column(
            "respuestas_encuesta",
            sa.Column("respuestas", sa.JSON(), nullable=True),
        )
        responses = sa.Table(
            "respuestas_encuesta", sa.MetaData(), autoload_with=bind
        )
        for response_id, comment in bind.execute(
            sa.select(responses.c.id, responses.c.comment)
        ):
            bind.execute(
                sa.update(responses)
                .where(responses.c.id == response_id)
                .values(respuestas={"q1": comment or ""})
            )

    response_columns = _column_names(bind, "respuestas_encuesta")
    if "estudiante_id" not in response_columns:
        with op.batch_alter_table("respuestas_encuesta") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "estudiante_id",
                    sa.Integer(),
                    sa.ForeignKey(
                        "estudiantes.user_id",
                        ondelete="CASCADE",
                        name="fk_respuestas_encuesta_estudiante",
                    ),
                    nullable=True,
                )
            )
        responses = sa.Table(
            "respuestas_encuesta", sa.MetaData(), autoload_with=bind
        )
        bind.execute(
            sa.update(responses).values(estudiante_id=responses.c.user_id)
        )

    response_columns = _column_names(bind, "respuestas_encuesta")
    unique_constraints = sa.inspect(bind).get_unique_constraints(
        "respuestas_encuesta"
    )
    foreign_keys = sa.inspect(bind).get_foreign_keys("respuestas_encuesta")
    with op.batch_alter_table(
        "respuestas_encuesta",
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
        },
    ) as batch_op:
        for constraint in unique_constraints:
            columns = set(constraint.get("column_names") or ())
            if {"actividad_id", "user_id"} <= columns:
                name = constraint.get("name") or (
                    "uq_respuestas_encuesta_actividad_id"
                )
                batch_op.drop_constraint(name, type_="unique")
        for foreign_key in foreign_keys:
            if (
                foreign_key.get("referred_table") == "users"
                and foreign_key.get("constrained_columns") == ["user_id"]
            ):
                batch_op.drop_constraint(
                    foreign_key.get("name")
                    or "fk_respuestas_encuesta_user_id_users",
                    type_="foreignkey",
                )
        if "user_id" in response_columns:
            batch_op.drop_column("user_id")
        if "comment" in response_columns:
            batch_op.drop_column("comment")
        if "respuestas" in response_columns:
            batch_op.alter_column(
                "respuestas",
                existing_type=sa.JSON(),
                nullable=False,
            )
    op.create_index(
        "uq_respuesta_actividad_estudiante",
        "respuestas_encuesta",
        ["actividad_id", "estudiante_id"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "respuestas_encuesta" in tables:
        responses = sa.Table(
            "respuestas_encuesta", sa.MetaData(), autoload_with=bind
        )
        if "respuestas" in responses.c:
            for answers, in bind.execute(sa.select(responses.c.respuestas)):
                if answers and set(answers) - {"q1"}:
                    raise RuntimeError(
                        "Cannot downgrade survey JSON containing answers beyond q1."
                    )

        op.add_column(
            "respuestas_encuesta",
            sa.Column("comment", sa.Text(), nullable=True),
        )
        with op.batch_alter_table("respuestas_encuesta") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "user_id",
                    sa.Integer(),
                    sa.ForeignKey(
                        "users.id",
                        ondelete="CASCADE",
                        name="fk_respuestas_encuesta_user",
                    ),
                    nullable=True,
                ),
            ),
        responses = sa.Table(
            "respuestas_encuesta", sa.MetaData(), autoload_with=bind
        )
        for response_id, answers, estudiante_id in bind.execute(
            sa.select(
                responses.c.id,
                responses.c.respuestas,
                responses.c.estudiante_id,
            )
        ):
            bind.execute(
                sa.update(responses)
                .where(responses.c.id == response_id)
                .values(
                    comment=(answers or {}).get("q1") or None,
                    user_id=estudiante_id,
                )
            )

        op.drop_index(
            "uq_respuesta_actividad_estudiante",
            table_name="respuestas_encuesta",
        )
        unique_constraints = sa.inspect(bind).get_unique_constraints(
            "respuestas_encuesta"
        )
        foreign_keys = sa.inspect(bind).get_foreign_keys("respuestas_encuesta")
        with op.batch_alter_table(
            "respuestas_encuesta",
            naming_convention={
                "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
                "uq": "uq_%(table_name)s_%(column_0_name)s",
            },
        ) as batch_op:
            for foreign_key in foreign_keys:
                if (
                    foreign_key.get("referred_table") == "estudiantes"
                    and foreign_key.get("constrained_columns")
                    == ["estudiante_id"]
                ):
                    batch_op.drop_constraint(
                        foreign_key.get("name")
                        or "fk_respuestas_encuesta_estudiante_id_estudiantes",
                        type_="foreignkey",
                    )
            batch_op.drop_column("estudiante_id")
            batch_op.drop_column("respuestas")
        op.rename_table("respuestas_encuesta", "survey_responses")
        op.create_index(
            "uq_survey_actividad_user",
            "survey_responses",
            ["actividad_id", "user_id"],
            unique=True,
        )

    if "actividades" in tables and "preguntas" in _column_names(
        bind, "actividades"
    ):
        activities = sa.Table("actividades", sa.MetaData(), autoload_with=bind)
        for preguntas, in bind.execute(sa.select(activities.c.preguntas)):
            if preguntas and set(preguntas) - {"q1"}:
                raise RuntimeError(
                    "Cannot downgrade activities containing survey questions beyond q1."
                )
        op.drop_column("actividades", "preguntas")

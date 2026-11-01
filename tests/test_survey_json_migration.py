import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def _migration():
    path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20261103_encuestas_json.py"
    )
    spec = spec_from_file_location("survey_json_migration", path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _create_legacy_schema(connection):
    connection.exec_driver_sql(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY
        )
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE estudiantes (
            user_id INTEGER PRIMARY KEY REFERENCES users(id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE actividades (
            id INTEGER PRIMARY KEY,
            encuesta_obligatoria BOOLEAN NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE survey_responses (
            id INTEGER PRIMARY KEY,
            actividad_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NULL,
            created_at DATETIME,
            CONSTRAINT fk_survey_activity FOREIGN KEY (actividad_id) REFERENCES actividades(id),
            CONSTRAINT fk_survey_user FOREIGN KEY (user_id) REFERENCES users(id),
            CONSTRAINT uq_survey_actividad_user UNIQUE (actividad_id, user_id)
        )
        """
    )


def test_upgrade_preserves_legacy_data_and_moves_responses_to_estudiantes():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        _create_legacy_schema(connection)
        connection.exec_driver_sql("INSERT INTO users VALUES (1), (2)")
        connection.exec_driver_sql("INSERT INTO estudiantes VALUES (1), (2)")
        connection.exec_driver_sql(
            "INSERT INTO actividades VALUES (1, TRUE), (2, FALSE)"
        )
        connection.exec_driver_sql(
            """
            INSERT INTO survey_responses
                (id, actividad_id, user_id, rating, comment)
            VALUES (1, 1, 1, 5, 'Muy buena')
            """
        )

        with Operations.context(MigrationContext.configure(connection)):
            _migration().upgrade()

        assert "survey_responses" not in inspect(connection).get_table_names()
        assert "respuestas_encuesta" in inspect(connection).get_table_names()
        activity_columns = {
            column["name"]: column
            for column in inspect(connection).get_columns("actividades")
        }
        assert activity_columns["preguntas"]["nullable"] is False
        assert json.loads(connection.exec_driver_sql(
            "SELECT preguntas FROM actividades WHERE id = 1"
        ).scalar_one()) == {"q1": "¿Qué te pareció la actividad?"}
        assert json.loads(connection.exec_driver_sql(
            "SELECT preguntas FROM actividades WHERE id = 2"
        ).scalar_one()) == {}

        response_columns = {
            column["name"]: column
            for column in inspect(connection).get_columns("respuestas_encuesta")
        }
        assert set(response_columns) == {
            "id",
            "actividad_id",
            "estudiante_id",
            "rating",
            "created_at",
            "respuestas",
        }
        assert response_columns["estudiante_id"]["nullable"] is True
        assert response_columns["rating"]["nullable"] is False
        response = connection.exec_driver_sql(
            "SELECT estudiante_id, rating, respuestas FROM respuestas_encuesta"
        ).one()
        assert (response[0], response[1], json.loads(response[2])) == (
            1,
            5,
            {"q1": "Muy buena"},
        )
        assert any(
            fk["referred_table"] == "estudiantes"
            and fk["constrained_columns"] == ["estudiante_id"]
            for fk in inspect(connection).get_foreign_keys("respuestas_encuesta")
        )
    engine.dispose()


def test_downgrade_restores_legacy_response_shape():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        _create_legacy_schema(connection)
        connection.exec_driver_sql("INSERT INTO users VALUES (1)")
        connection.exec_driver_sql("INSERT INTO estudiantes VALUES (1)")
        connection.exec_driver_sql("INSERT INTO actividades VALUES (1, TRUE)")
        connection.exec_driver_sql(
            """
            INSERT INTO survey_responses
                (id, actividad_id, user_id, rating, comment)
            VALUES (1, 1, 1, 5, 'Respuesta')
            """
        )

        with Operations.context(MigrationContext.configure(connection)):
            _migration().upgrade()
            _migration().downgrade()

        assert "survey_responses" in inspect(connection).get_table_names()
        assert "respuestas_encuesta" not in inspect(connection).get_table_names()
        response_columns = {
            column["name"]: column
            for column in inspect(connection).get_columns("survey_responses")
        }
        assert "comment" in response_columns
        assert "respuestas" not in response_columns
        assert connection.exec_driver_sql(
            "SELECT user_id, rating, comment FROM survey_responses"
        ).one() == (1, 5, "Respuesta")
        assert "preguntas" not in {
            column["name"] for column in inspect(connection).get_columns("actividades")
        }
    engine.dispose()

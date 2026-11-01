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
        / "20261104_estudiante_resp_required.py"
    )
    spec = spec_from_file_location("survey_student_required_migration", path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_upgrade_requires_estudiante_and_downgrade_restores_nullability():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE respuestas_encuesta (
                id INTEGER PRIMARY KEY,
                estudiante_id INTEGER NULL
            )
            """
        )
        connection.exec_driver_sql(
            "INSERT INTO respuestas_encuesta VALUES (1, 7)"
        )

        with Operations.context(MigrationContext.configure(connection)):
            _migration().upgrade()

        column = next(
            item
            for item in inspect(connection).get_columns("respuestas_encuesta")
            if item["name"] == "estudiante_id"
        )
        assert column["nullable"] is False

        with Operations.context(MigrationContext.configure(connection)):
            _migration().downgrade()

        column = next(
            item
            for item in inspect(connection).get_columns("respuestas_encuesta")
            if item["name"] == "estudiante_id"
        )
        assert column["nullable"] is True
    engine.dispose()

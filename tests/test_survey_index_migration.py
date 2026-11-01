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
        / "20261106_fix_survey_index.py"
    )
    spec = spec_from_file_location("survey_index_migration", path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_upgrade_renames_legacy_activity_index_and_downgrade_restores_it():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE respuestas_encuesta (id INTEGER PRIMARY KEY, actividad_id INTEGER)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX ix_survey_responses_actividad_id "
            "ON respuestas_encuesta (actividad_id)"
        )

        with Operations.context(MigrationContext.configure(connection)):
            _migration().upgrade()

        names = {
            index["name"]
            for index in inspect(connection).get_indexes("respuestas_encuesta")
        }
        assert "ix_survey_responses_actividad_id" not in names
        assert "ix_respuestas_encuesta_actividad_id" in names

        with Operations.context(MigrationContext.configure(connection)):
            _migration().downgrade()

        names = {
            index["name"]
            for index in inspect(connection).get_indexes("respuestas_encuesta")
        }
        assert "ix_respuestas_encuesta_actividad_id" not in names
        assert "ix_survey_responses_actividad_id" in names
    engine.dispose()

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
        / "20261105_drop_actividad_docente.py"
    )
    spec = spec_from_file_location("drop_actividad_docente", path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _create_schema(connection):
    connection.exec_driver_sql(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, persona_id INTEGER)"
    )
    connection.exec_driver_sql(
        "CREATE TABLE personas (id INTEGER PRIMARY KEY)"
    )
    connection.exec_driver_sql(
        "CREATE TABLE docentes (id INTEGER PRIMARY KEY, persona_id INTEGER)"
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE actividades (
            id INTEGER PRIMARY KEY,
            titulo VARCHAR(200) NOT NULL,
            docente_id INTEGER,
            CONSTRAINT actividades_docente_id_fkey
                FOREIGN KEY (docente_id) REFERENCES users(id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE actividad_docente (
            actividad_id INTEGER NOT NULL REFERENCES actividades(id),
            docente_id INTEGER NOT NULL REFERENCES docentes(id),
            PRIMARY KEY (actividad_id, docente_id)
        )
        """
    )


def test_upgrade_drops_legacy_column_and_preserves_association_rows():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        _create_schema(connection)
        connection.exec_driver_sql("INSERT INTO users VALUES (1, 10)")
        connection.exec_driver_sql("INSERT INTO personas VALUES (10)")
        connection.exec_driver_sql("INSERT INTO docentes VALUES (20, 10)")
        connection.exec_driver_sql("INSERT INTO actividades VALUES (30, 'Taller', 1)")
        connection.exec_driver_sql("INSERT INTO actividad_docente VALUES (30, 20)")

        with Operations.context(MigrationContext.configure(connection)):
            _migration().upgrade()

        columns = {
            column["name"]
            for column in inspect(connection).get_columns("actividades")
        }
        assert columns == {"id", "titulo"}
        assert inspect(connection).get_foreign_keys("actividades") == []
        assert connection.exec_driver_sql(
            "SELECT actividad_id, docente_id FROM actividad_docente"
        ).one() == (30, 20)
    engine.dispose()


def test_downgrade_restores_legacy_column_for_unambiguous_teacher_links():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        _create_schema(connection)
        connection.exec_driver_sql("INSERT INTO users VALUES (1, 10)")
        connection.exec_driver_sql("INSERT INTO personas VALUES (10)")
        connection.exec_driver_sql("INSERT INTO docentes VALUES (20, 10)")
        connection.exec_driver_sql("INSERT INTO actividades VALUES (30, 'Taller', NULL)")
        connection.exec_driver_sql("INSERT INTO actividad_docente VALUES (30, 20)")

        with Operations.context(MigrationContext.configure(connection)):
            _migration().upgrade()
            _migration().downgrade()

        columns = {
            column["name"]: column
            for column in inspect(connection).get_columns("actividades")
        }
        assert columns["docente_id"]["nullable"] is True
        assert connection.exec_driver_sql(
            "SELECT docente_id FROM actividades WHERE id = 30"
        ).scalar_one() == 1
    engine.dispose()

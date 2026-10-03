import os
from pathlib import Path
import subprocess
import sys

import sqlalchemy as sa


def test_fresh_database_migrations_and_rollback(tmp_path):
    backend_directory = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    environment = {**os.environ, "DATABASE_URL": database_url}
    command = [sys.executable, "-m", "alembic", "-c", str(backend_directory / "alembic.ini")]

    result = subprocess.run(command + ["upgrade", "head"], cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    engine = sa.create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == "20260904_0004"
        assert {"users", "evidence_objects", "road_segments"}.issubset(sa.inspect(connection).get_table_names())
    engine.dispose()

    subprocess.run(command + ["upgrade", "head"], cwd=tmp_path, env=environment, check=True, capture_output=True, text=True)
    subprocess.run(command + ["downgrade", "base"], cwd=tmp_path, env=environment, check=True, capture_output=True, text=True)
    engine = sa.create_engine(database_url)
    assert sa.inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()

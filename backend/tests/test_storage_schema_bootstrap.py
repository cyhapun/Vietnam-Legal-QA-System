from unittest.mock import patch

from app.services.storage import _ensure_schema


def test_ensure_schema_executes_sql_statements():
    fake_cursor = object()

    class FakeConnection:
        def __init__(self):
            self.cursor_calls = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def cursor(self):
            self.cursor_calls += 1
            return self

        def execute(self, sql):
            assert "CREATE TABLE IF NOT EXISTS laws" in sql
            assert "CREATE TABLE IF NOT EXISTS clauses" in sql
            assert "CREATE TABLE IF NOT EXISTS indexing_runs" in sql

    fake_conn = FakeConnection()

    with patch("psycopg.connect", return_value=fake_conn):
        _ensure_schema()

    assert fake_conn.cursor_calls == 1

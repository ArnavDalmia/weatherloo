"""Small sqlite3 data-access layer."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any

from app.models import SCHEMA_STATEMENTS, TABLE_COLUMNS


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)
            connection.commit()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def insert(self, sql: str, parameters: Sequence[Any]) -> int:
        with self.connection() as connection:
            cursor = connection.execute(sql, parameters)
            connection.commit()
            return int(cursor.lastrowid)

    def save_survey_answer(self, values: dict[str, Any]) -> tuple[int, bool]:
        """Insert or update an answer, returning (row id, was_created)."""
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT id
                FROM survey_answers
                WHERE survey_session_id = ? AND question_id = ?
                """,
                (values["survey_session_id"], values["question_id"]),
            ).fetchone()

            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO survey_answers (
                        survey_session_id, location_id, pod_id, question_id,
                        response_value, answered_at, received_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        values["survey_session_id"],
                        values["location_id"],
                        values["pod_id"],
                        values["question_id"],
                        values["response_value"],
                        values["answered_at"],
                        values["received_at"],
                    ),
                )
                row_id = int(cursor.lastrowid)
                created = True
            else:
                row_id = int(existing["id"])
                connection.execute(
                    """
                    UPDATE survey_answers
                    SET location_id = ?, pod_id = ?, response_value = ?,
                        answered_at = ?, received_at = ?
                    WHERE id = ?
                    """,
                    (
                        values["location_id"],
                        values["pod_id"],
                        values["response_value"],
                        values["answered_at"],
                        values["received_at"],
                        row_id,
                    ),
                )
                created = False

            connection.commit()
            return row_id, created

    def query(
        self, sql: str, parameters: Sequence[Any] = ()
    ) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(sql, parameters).fetchall()
            return [dict(row) for row in rows]

    def fetch_table(self, table: str) -> tuple[tuple[str, ...], list[sqlite3.Row]]:
        columns = TABLE_COLUMNS[table]
        column_sql = ", ".join(columns)
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT {column_sql} FROM {table} ORDER BY id ASC"
            ).fetchall()
        return columns, rows

    def clear_table(self, table: str) -> int:
        """Delete every row from a known table. Callers must only pass a
        table name from TABLE_COLUMNS, never raw user input."""
        if table not in TABLE_COLUMNS:
            raise ValueError(f"Unknown table: {table}")

        with self.connection() as connection:
            cursor = connection.execute(f"DELETE FROM {table}")
            connection.commit()
            return cursor.rowcount

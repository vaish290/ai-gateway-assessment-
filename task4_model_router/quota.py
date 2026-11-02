
import sqlite3
import time
from pathlib import Path
from contextlib import closing


TOKEN_LIMIT = 50_000
WINDOW_SECONDS = 60


class TokenQuota:
    def __init__(self, db_path="quota.db"):
        self.db_path = str(Path(db_path))
        self._initialize_database()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=10.0
        )

        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize_database(self):
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS token_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        tokens INTEGER NOT NULL,
                        timestamp REAL NOT NULL
                    )
                """)

                connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tenant_time
                    ON token_usage (tenant_id, timestamp)
                """)

    def check_and_consume(
        self,
        tenant_id: str,
        tokens: int,
        now: float | None = None
    ) -> bool:
        """
        Atomically check and reserve tokens for a tenant.

        Returns True if allowed, False if quota exceeded.
        """

        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("Invalid tenant ID")

        if type(tokens) is not int or tokens <= 0:
            raise ValueError("Tokens must be a positive integer")

        if now is None:
            now = time.time()

        cutoff = now - WINDOW_SECONDS

        with closing(self._connect()) as connection:
            try:
                # Lock database before checking quota.
                connection.execute("BEGIN IMMEDIATE")

                # Remove expired usage records.
                connection.execute(
                    """
                    DELETE FROM token_usage
                    WHERE timestamp <= ?
                    """,
                    (cutoff,)
                )

                # Get current usage for this tenant.
                row = connection.execute(
                    """
                    SELECT COALESCE(SUM(tokens), 0)
                    FROM token_usage
                    WHERE tenant_id = ?
                      AND timestamp > ?
                      AND timestamp <= ?
                    """,
                    (tenant_id, cutoff, now)
                ).fetchone()

                used_tokens = row[0]

                if used_tokens + tokens > TOKEN_LIMIT:
                    connection.rollback()
                    return False

                # Record the new token reservation.
                connection.execute(
                    """
                    INSERT INTO token_usage (
                        tenant_id,
                        tokens,
                        timestamp
                    )
                    VALUES (?, ?, ?)
                    """,
                    (tenant_id, tokens, now)
                )

                connection.commit()
                return True

            except Exception:
                connection.rollback()
                raise

    def get_usage(
        self,
        tenant_id: str,
        now: float | None = None
    ) -> int:
        """Return tokens used during the rolling window."""

        if now is None:
            now = time.time()

        cutoff = now - WINDOW_SECONDS

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT COALESCE(SUM(tokens), 0)
                FROM token_usage
                WHERE tenant_id = ?
                  AND timestamp > ?
                  AND timestamp <= ?
                """,
                (tenant_id, cutoff, now)
            ).fetchone()

        return row[0]

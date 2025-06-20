import json
import pickle
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..utils.config import Config


class CacheManager:
    """Manages local caching of Report Portal data."""

    def __init__(self, config: Config):
        self.cache_dir = Path(config.cache.directory)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self.ttl_hours = config.cache.ttl_hours
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for caching."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON cache(expires_at)
            """
            )

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if not expired."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT value, expires_at FROM cache
                WHERE key = ? AND expires_at > ?
            """,
                (key, datetime.now()),
            )

            result = cursor.fetchone()
            if result:
                value_blob, _ = result
                return pickle.loads(value_blob)  # nosec B301

        return None

    def set(self, key: str, value: Any, ttl_hours: Optional[int] = None):
        """Store value in cache with TTL."""
        ttl = ttl_hours or self.ttl_hours
        expires_at = datetime.now() + timedelta(hours=ttl)

        value_blob = pickle.dumps(value)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            """,
                (key, value_blob, datetime.now(), expires_at),
            )

    def clear_expired(self):
        """Remove expired entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM cache WHERE expires_at < ?
            """,
                (datetime.now(),),
            )

        logger.info("Cleared expired cache entries")

    def clear_all(self):
        """Clear entire cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")

        logger.info("Cleared all cache entries")

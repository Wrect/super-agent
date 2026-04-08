"""
Session memory for Omni Browser Agent.
Manages session history with LRU caching and optional Redis persistence.
"""

import asyncio
import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.logger import get_component_logger
from core.config import get_settings
from models.schemas import SessionHistory, BrowserTask, TaskResult


class SessionMemory:
    """
    Session history manager with LRU caching and optional Redis persistence.
    Thread-safe via asyncio.Lock.
    """

    def __init__(self, max_entries: Optional[int] = None):
        self.logger = get_component_logger("memory")
        self.settings = get_settings()

        self.max_entries = max_entries or self.settings.debate.max_history_entries
        self._history: OrderedDict[str, SessionHistory] = OrderedDict()
        self._lock = asyncio.Lock()

        self._redis_client = None
        if self.settings.debate.enable_redis_persistence:
            self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis

            self._redis_client = redis.Redis(
                host=self.settings.redis.host,
                port=self.settings.redis.port,
                password=self.settings.redis.password,
                db=self.settings.redis.db,
                decode_responses=True,
            )
            self.logger.info("Redis connection established for session history")
        except Exception as e:
            self.logger.warning(f"Failed to connect to Redis: {e}")
            self._redis_client = None

    async def add(self, entry: SessionHistory) -> None:
        """
        Add a session history entry.

        Args:
            entry: SessionHistory entry to add
        """
        async with self._lock:
            self._history[entry.id] = entry

            # Evict oldest entries if over limit
            while len(self._history) > self.max_entries:
                oldest_id = next(iter(self._history))
                self.logger.debug(f"Evicting oldest entry: {oldest_id}")
                del self._history[oldest_id]

            # Persist to Redis if available
            if self._redis_client:
                try:
                    key = f"session:{entry.id}"
                    self._redis_client.set(
                        key,
                        entry.model_dump_json(),
                        ex=86400 * 7,  # 7 days TTL
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to persist to Redis: {e}")

    async def get(self, entry_id: str) -> Optional[SessionHistory]:
        """
        Get a session history entry by ID.

        Args:
            entry_id: Entry ID to retrieve

        Returns:
            SessionHistory entry or None if not found
        """
        async with self._lock:
            # Try memory first
            if entry_id in self._history:
                # Move to end (most recently used)
                self._history.move_to_end(entry_id)
                return self._history[entry_id]

            # Try Redis
            if self._redis_client:
                try:
                    key = f"session:{entry_id}"
                    data = self._redis_client.get(key)
                    if data:
                        entry = SessionHistory.model_validate_json(data)
                        # Add to memory cache
                        async with self._lock:
                            self._history[entry_id] = entry
                        return entry
                except Exception as e:
                    self.logger.warning(f"Failed to fetch from Redis: {e}")

            return None

    async def get_recent(self, limit: int = 10) -> List[SessionHistory]:
        """
        Get most recent session history entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of recent SessionHistory entries
        """
        async with self._lock:
            entries = list(self._history.values())
            return entries[-limit:] if len(entries) > limit else entries

    async def search(self, query: str, limit: int = 10) -> List[SessionHistory]:
        """
        Search session history by task description.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching SessionHistory entries
        """
        async with self._lock:
            query_lower = query.lower()
            matches = []

            for entry in reversed(self._history.values()):
                if query_lower in entry.task.description.lower():
                    matches.append(entry)
                    if len(matches) >= limit:
                        break

            return matches

    async def get_all(self) -> List[SessionHistory]:
        """Get all session history entries."""
        async with self._lock:
            return list(self._history.values())

    async def delete(self, entry_id: str) -> bool:
        """
        Delete a session history entry.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if entry was deleted
        """
        async with self._lock:
            if entry_id in self._history:
                del self._history[entry_id]

                if self._redis_client:
                    try:
                        self._redis_client.delete(f"session:{entry_id}")
                    except Exception as e:
                        self.logger.warning(f"Failed to delete from Redis: {e}")

                return True

            return False

    async def clear(self) -> None:
        """Clear all session history."""
        async with self._lock:
            self._history.clear()

            if self._redis_client:
                try:
                    for key in self._redis_client.keys("session:*"):
                        self._redis_client.delete(key)
                except Exception as e:
                    self.logger.warning(f"Failed to clear Redis: {e}")

    async def load_from_disk(self, path: str) -> None:
        """
        Load session history from disk file.

        Args:
            path: Path to JSON file
        """
        file_path = Path(path)

        if not file_path.exists():
            self.logger.warning(f"Session history file not found: {path}")
            return

        try:
            data = file_path.read_text()
            entries = json.loads(data)

            async with self._lock:
                for entry_data in entries:
                    entry = SessionHistory.model_validate(entry_data)
                    self._history[entry.id] = entry

            self.logger.info(f"Loaded {len(entries)} entries from {path}")

        except Exception as e:
            self.logger.error(f"Failed to load session history: {e}")

    async def save_to_disk(self, path: str) -> None:
        """
        Save session history to disk file.

        Args:
            path: Path to JSON file
        """
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with self._lock:
            entries = [entry.model_dump() for entry in self._history.values()]

        try:
            file_path.write_text(json.dumps(entries, indent=2, default=str))
            self.logger.info(f"Saved {len(entries)} entries to {path}")
        except Exception as e:
            self.logger.error(f"Failed to save session history: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "total_entries": len(self._history),
            "max_entries": self.max_entries,
            "redis_enabled": self._redis_client is not None,
            "redis_connected": False,  # Would check actual connection
        }


# Global memory instance
_session_memory: Optional[SessionMemory] = None


def get_session_memory() -> SessionMemory:
    """Get singleton session memory instance."""
    global _session_memory
    if _session_memory is None:
        _session_memory = SessionMemory()
    return _session_memory

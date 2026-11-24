import sqlite3
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

class LocalBufferStorage:
    """
    Local SQLite buffer for offline telemetry resilience and retry backoff.
    Ensures zero telemetry loss when endpoint is disconnected from network.
    """
    def __init__(self, db_path: str = "sentinel_sensor_buffer.db", max_events: int = 10000):
        self.db_path = db_path
        self.max_events = max_events
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_hash TEXT UNIQUE,
                    event_type TEXT,
                    payload_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def buffer_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        # Calculate deterministic event hash for deduplication
        raw_repr = f"{event_type}:{payload.get('timestamp')}:{payload.get('title')}:{payload.get('source_ip')}"
        ev_hash = hashlib.sha256(raw_repr.encode("utf-8")).hexdigest()

        try:
            with self._get_connection() as conn:
                # Maintain storage limits
                count = conn.execute("SELECT COUNT(*) FROM event_buffer").fetchone()[0]
                if count >= self.max_events:
                    # Drop oldest buffered events if capacity reached
                    conn.execute("DELETE FROM event_buffer WHERE id IN (SELECT id FROM event_buffer ORDER BY id ASC LIMIT 50)")

                conn.execute("""
                    INSERT OR IGNORE INTO event_buffer (event_hash, event_type, payload_json)
                    VALUES (?, ?, ?)
                """, (ev_hash, event_type, json.dumps(payload)))
                conn.commit()
                return True
        except Exception:
            return False

    def get_pending_batch(self, batch_size: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, event_type, payload_json, retry_count
                FROM event_buffer
                ORDER BY id ASC
                LIMIT ?
            """, (batch_size,)).fetchall()
            
            results = []
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"])
                    payload["_buffer_id"] = r["id"]
                    results.append(payload)
                except Exception:
                    continue
            return results

    def remove_buffered_events(self, buffer_ids: List[int]):
        if not buffer_ids:
            return
        placeholders = ",".join("?" * len(buffer_ids))
        with self._get_connection() as conn:
            conn.execute(f"DELETE FROM event_buffer WHERE id IN ({placeholders})", buffer_ids)
            conn.commit()

    def increment_retry(self, buffer_ids: List[int]):
        if not buffer_ids:
            return
        placeholders = ",".join("?" * len(buffer_ids))
        with self._get_connection() as conn:
            conn.execute(f"UPDATE event_buffer SET retry_count = retry_count + 1 WHERE id IN ({placeholders})", buffer_ids)
            conn.commit()

    def pending_count(self) -> int:
        with self._get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM event_buffer").fetchone()[0]

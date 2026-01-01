import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from config import DB_PATH


def init_db():
    """Initialize the database and create tables if they don't exist."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                embedding TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        conn.commit()


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def cleanup_old_tasks() -> int:
    """Delete tasks older than 1 hour. Returns number of deleted tasks."""
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM tasks WHERE created_at < datetime('now', '-1 hour')"
        )
        conn.commit()
        return result.rowcount


def create_task(text: str) -> str:
    """Create a new task and return its ID. Also cleans up old tasks."""
    # Cleanup old tasks (older than 1 hour)
    cleanup_old_tasks()

    task_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO tasks (id, text) VALUES (?, ?)",
            (task_id, text)
        )
        conn.commit()
    return task_id


def get_task(task_id: str) -> Optional[dict]:
    """Get a task by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()
        if row:
            return dict(row)
    return None


def claim_next_task() -> Optional[dict]:
    """Atomically claim the next pending task for processing.

    Uses conditional UPDATE to prevent race conditions - if another worker
    claims the task between SELECT and UPDATE, rowcount will be 0.
    """
    with get_connection() as conn:
        # Find a pending task
        row = conn.execute(
            "SELECT id, text FROM tasks WHERE status = 'pending' ORDER BY created_at LIMIT 1"
        ).fetchone()

        if not row:
            return None

        # Atomically claim ONLY if still pending (prevents race condition)
        result = conn.execute(
            "UPDATE tasks SET status = 'processing', updated_at = ? WHERE id = ? AND status = 'pending'",
            (datetime.utcnow().isoformat(), row["id"])
        )
        conn.commit()

        # If rowcount is 0, another worker claimed it first
        if result.rowcount == 0:
            return None

        return {"id": row["id"], "text": row["text"], "status": "processing"}


def complete_task(task_id: str, embedding: list[float]) -> bool:
    """Mark a task as completed with its embedding result."""
    with get_connection() as conn:
        result = conn.execute(
            """UPDATE tasks
               SET status = 'completed', embedding = ?, updated_at = ?
               WHERE id = ? AND status = 'processing'""",
            (json.dumps(embedding), datetime.utcnow().isoformat(), task_id)
        )
        conn.commit()
        return result.rowcount > 0


def fail_task(task_id: str, error: str) -> bool:
    """Mark a task as failed with an error message."""
    with get_connection() as conn:
        result = conn.execute(
            """UPDATE tasks
               SET status = 'failed', error = ?, updated_at = ?
               WHERE id = ? AND status = 'processing'""",
            (error, datetime.utcnow().isoformat(), task_id)
        )
        conn.commit()
        return result.rowcount > 0


def delete_task(task_id: str) -> bool:
    """Delete a task from the database."""
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )
        conn.commit()
        return result.rowcount > 0

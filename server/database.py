import aiosqlite
import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import asyncio

from config import DB_PATH


_db_pool = None
_cleanup_task = None


async def init_db():
    """Initialize the database and create tables if they don't exist."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT DEFAULT 'embedding',
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                result TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
        await db.commit()


async def cleanup_old_tasks() -> int:
    """Delete tasks older than 1 hour. Returns number of deleted tasks."""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "DELETE FROM tasks WHERE created_at < datetime('now', '-1 hour')"
        )
        await conn.commit()
        return cursor.rowcount


async def create_task(task_type: str, payload: dict) -> str:
    """Create a new task and return its ID."""
    task_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO tasks (id, task_type, payload) VALUES (?, ?, ?)",
            (task_id, task_type, json.dumps(payload))
        )
        await conn.commit()
    return task_id


async def get_task(task_id: str) -> Optional[dict]:
    """Get a task by ID."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None


async def claim_next_task() -> Optional[dict]:
    """Atomically claim the next pending task for processing.

    Uses conditional UPDATE to prevent race conditions - if another worker
    claims the task between SELECT and UPDATE, rowcount will be 0.
    """
    async with aiosqlite.connect(DB_PATH) as conn:
        # Find a pending task
        cursor = await conn.execute(
            "SELECT id, task_type, payload FROM tasks WHERE status = 'pending' ORDER BY created_at LIMIT 1"
        )
        row = await cursor.fetchone()

        if not row:
            return None

        # Atomically claim ONLY if still pending (prevents race condition)
        cursor = await conn.execute(
            "UPDATE tasks SET status = 'processing', updated_at = ? WHERE id = ? AND status = 'pending'",
            (datetime.utcnow().isoformat(), row[0])
        )
        await conn.commit()

        # If rowcount is 0, another worker claimed it first
        if cursor.rowcount == 0:
            return None

        return {
            "id": row[0],
            "task_type": row[1],
            "payload": json.loads(row[2]),
            "status": "processing"
        }


async def complete_task(task_id: str, result_data: any) -> bool:
    """Mark a task as completed with its result."""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            """UPDATE tasks
               SET status = 'completed', result = ?, updated_at = ?
               WHERE id = ? AND status = 'processing'""",
            (json.dumps(result_data), datetime.utcnow().isoformat(), task_id)
        )
        await conn.commit()
        return cursor.rowcount > 0


async def fail_task(task_id: str, error: str) -> bool:
    """Mark a task as failed with an error message."""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            """UPDATE tasks
               SET status = 'failed', error = ?, updated_at = ?
               WHERE id = ? AND status = 'processing'""",
            (error, datetime.utcnow().isoformat(), task_id)
        )
        await conn.commit()
        return cursor.rowcount > 0


async def delete_task(task_id: str) -> bool:
    """Delete a task from the database."""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )
        await conn.commit()
        return cursor.rowcount > 0

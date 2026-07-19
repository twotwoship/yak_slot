import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "slotguard.db"


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect_db()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id      INTEGER NOT NULL,
                slot         INTEGER NOT NULL
                             CHECK(slot BETWEEN 1 AND 10),
                scheduled_at TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'WAITING'
                             CHECK(status IN (
                                 'WAITING',
                                 'ALLOWED',
                                 'DISPENSED',
                                 'MISSED'
                             )),
                dispensed_at TEXT,
                synced       INTEGER NOT NULL DEFAULT 0
                             CHECK(synced IN (0, 1)),

                UNIQUE(pack_id, slot)
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


def create_schedule(pack_id, slot, scheduled_at):
    conn = connect_db()

    try:
        cursor = conn.execute(
            """
            INSERT INTO schedules (
                pack_id,
                slot,
                scheduled_at
            )
            VALUES (?, ?, ?)
            """,
            (pack_id, slot, scheduled_at),
        )

        conn.commit()
        return cursor.lastrowid

    finally:
        conn.close()


def get_schedules():
    conn = connect_db()

    try:
        rows = conn.execute(
            """
            SELECT
                id,
                pack_id,
                slot,
                scheduled_at,
                status,
                dispensed_at,
                synced
            FROM schedules
            ORDER BY scheduled_at, slot
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def allow_due_schedules(scheduled_at):
    conn = connect_db()

    try:
        cursor = conn.execute(
            """
            UPDATE schedules
            SET status = 'ALLOWED'
            WHERE scheduled_at = ?
              AND status = 'WAITING'
            """,
            (scheduled_at,),
        )

        conn.commit()
        return cursor.rowcount

    finally:
        conn.close()


def mark_synced(schedule_id):
    conn = connect_db()

    try:
        conn.execute(
            """
            UPDATE schedules
            SET synced = 1
            WHERE id = ?
            """,
            (schedule_id,),
        )

        conn.commit()

    finally:
        conn.close()


def update_status(schedule_id, status, event_time=None):
    conn = connect_db()

    try:
        if status == "DISPENSED":
            conn.execute(
                """
                UPDATE schedules
                SET status = ?,
                    dispensed_at = ?
                WHERE id = ?
                """,
                (status, event_time, schedule_id),
            )
        else:
            conn.execute(
                """
                UPDATE schedules
                SET status = ?
                WHERE id = ?
                """,
                (status, schedule_id),
            )

        conn.commit()

    finally:
        conn.close()

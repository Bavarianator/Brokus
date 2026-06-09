"""Database layer for brokus using SQLite."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import aiosqlite

from brokus.utils.logger import log


# ── Projekt-Root ermitteln (egal wo brokus gestartet wird) ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = _PROJECT_ROOT / "data" / "projects.db"


def get_db_path() -> Path:
    return DB_PATH


def get_books_dir() -> Path:
    """Return the books export directory (absolute, project-root based)."""
    return _PROJECT_ROOT / "data" / "books"


def get_project_root() -> Path:
    """Return the absolute project root."""
    return _PROJECT_ROOT


async def init_db():
    """Initialize the database schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                genre TEXT NOT NULL,
                idea TEXT NOT NULL,
                core_elements TEXT,          -- JSON
                synopsis TEXT,
                characters TEXT,             -- JSON array
                chapter_plan TEXT,           -- JSON array
                total_chapters INTEGER DEFAULT 20,
                chapters_completed INTEGER DEFAULT 0,
                total_words INTEGER DEFAULT 0,
                status TEXT DEFAULT 'draft', -- draft|generating|paused|completed|failed
                model TEXT DEFAULT 'claude-sonnet-4-20250514',
                config TEXT,                 -- JSON: project-specific overrides
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                number INTEGER NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                word_count INTEGER DEFAULT 0,
                compliance_score INTEGER,
                status TEXT DEFAULT 'planned',  -- planned|generating|completed|failed
                elements_covered TEXT,          -- JSON array of element IDs
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, number)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS generation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                chapter_number INTEGER,
                event TEXT NOT NULL,
                level TEXT DEFAULT 'INFO',
                details TEXT,               -- JSON
                timestamp TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        await db.commit()
        log.info("Database initialized")


async def create_project(
    title: str,
    genre: str,
    idea: str,
    total_chapters: int = 20,
    model: str = "claude-sonnet-4-20250514",
) -> int:
    """Create a new project and return its ID."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute(
            """INSERT INTO projects (title, genre, idea, total_chapters, model)
               VALUES (?, ?, ?, ?, ?)""",
            (title, genre, idea, total_chapters, model),
        )
        await db.commit()
        project_id = cursor.lastrowid
        log.info(f"Project created: '{title}' (ID: {project_id})")
        return project_id


async def get_project(project_id: int) -> Optional[dict]:
    """Get a project by ID."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)


async def get_all_projects() -> list[dict]:
    """Get all projects, ordered by most recent."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        )
        return [dict(row) for row in await cursor.fetchall()]


async def update_project(project_id: int, **kwargs):
    """Update project fields."""
    if not kwargs:
        return

    kwargs["updated_at"] = datetime.now().isoformat()

    # Handle total_words accumulation
    if "total_words" in kwargs:
        current = await get_project(project_id)
        if current:
            kwargs["total_words"] = current.get("total_words", 0) + kwargs["total_words"]

    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [project_id]

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            f"UPDATE projects SET {fields} WHERE id = ?", values
        )
        await db.commit()


async def save_chapter(
    project_id: int,
    number: int,
    title: str,
    text: str = "",
    word_count: int = 0,
    compliance_score: Optional[int] = None,
    status: str = "planned",
    elements_covered: Optional[list[str]] = None,
):
    """Insert or update a chapter."""
    elements_json = json.dumps(elements_covered or [])

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """INSERT INTO chapters (project_id, number, title, text, word_count,
               compliance_score, status, elements_covered, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(project_id, number) DO UPDATE SET
               title=excluded.title, text=excluded.text, word_count=excluded.word_count,
               compliance_score=excluded.compliance_score, status=excluded.status,
               elements_covered=excluded.elements_covered, updated_at=datetime('now')""",
            (project_id, number, title, text, word_count, compliance_score,
             status, elements_json),
        )
        await db.commit()


async def get_chapter(project_id: int, number: int) -> Optional[dict]:
    """Get a single chapter."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM chapters WHERE project_id = ? AND number = ?",
            (project_id, number),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_chapters(project_id: int) -> list[dict]:
    """Get all chapters for a project, ordered by number."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM chapters WHERE project_id = ? ORDER BY number",
            (project_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def log_generation_event(
    project_id: int,
    event: str,
    level: str = "INFO",
    chapter_number: Optional[int] = None,
    details: Optional[dict] = None,
):
    """Log a generation event."""
    details_json = json.dumps(details or {})

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """INSERT INTO generation_log (project_id, chapter_number, event, level, details)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, chapter_number, event, level, details_json),
        )
        await db.commit()


async def delete_project(project_id: int):
    """Delete a project and all associated data."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        log.info(f"Project {project_id} deleted")

"""Database connection and queries."""

import json
from pathlib import Path
from typing import Any

import asyncpg

from config import settings
from models import Leaderboard, Submission

_pool: asyncpg.Pool | None = None


async def init_db():
    """Initialize database connection pool and run migrations."""
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url)
    await run_migrations()


async def run_migrations():
    """Run SQL migrations."""
    migrations_dir = Path(__file__).parent / "migrations"
    
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        rows = await conn.fetch("SELECT name FROM _migrations")
        applied = {row["name"] for row in rows}
        
        for migration_file in sorted(migrations_dir.glob("*.sql")):
            if migration_file.name.endswith(".down.sql"):
                continue
            if migration_file.name in applied:
                continue
            
            print(f"Applying migration: {migration_file.name}")
            sql = migration_file.read_text()
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO _migrations (name) VALUES ($1)",
                migration_file.name
            )


async def close_db():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# Leaderboard queries

async def get_leaderboard_by_repo_id(github_repo_id: int) -> Leaderboard | None:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM leaderboards WHERE github_repo_id = $1",
            github_repo_id
        )
        return Leaderboard.from_row(dict(row)) if row else None


async def get_leaderboard_by_repo_name(repo_full_name: str) -> Leaderboard | None:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM leaderboards WHERE repo_full_name = $1",
            repo_full_name
        )
        return Leaderboard.from_row(dict(row)) if row else None


async def create_leaderboard(
    github_repo_id: int,
    repo_full_name: str,
    installation_id: int,
) -> Leaderboard:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO leaderboards (github_repo_id, repo_full_name, installation_id)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            github_repo_id, repo_full_name, installation_id
        )
        return Leaderboard.from_row(dict(row))


async def update_leaderboard_repo_name(github_repo_id: int, repo_full_name: str):
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE leaderboards SET repo_full_name = $1 WHERE github_repo_id = $2",
            repo_full_name, github_repo_id
        )


# Submission queries

async def get_submission_by_run_id(workflow_run_id: int) -> Submission | None:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM submissions WHERE workflow_run_id = $1",
            workflow_run_id
        )
        return Submission.from_row(dict(row)) if row else None


async def create_submission(
    workflow_run_id: int,
    leaderboard_repo: str,
    purple_repo: str,
    purple_owner: str,
    status: str,
    error_message: str | None = None,
    pr_url: str | None = None,
    pr_number: int | None = None,
    results_json: dict[str, Any] | None = None,
) -> Submission:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO submissions 
            (workflow_run_id, leaderboard_repo, purple_repo, purple_owner, status, 
             error_message, pr_url, pr_number, results_json)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            workflow_run_id, leaderboard_repo, purple_repo, purple_owner, status,
            error_message, pr_url, pr_number, json.dumps(results_json) if results_json else None
        )
        return Submission.from_row(dict(row))

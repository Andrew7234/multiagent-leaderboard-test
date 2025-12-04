"""Database models as dataclasses."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Leaderboard:
    id: int
    github_repo_id: int
    repo_full_name: str
    installation_id: int
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Leaderboard":
        return cls(
            id=row["id"],
            github_repo_id=row["github_repo_id"],
            repo_full_name=row["repo_full_name"],
            installation_id=row["installation_id"],
            created_at=row.get("created_at"),
        )


@dataclass
class Submission:
    id: int
    workflow_run_id: int
    leaderboard_repo: str
    purple_repo: str
    purple_owner: str
    status: str
    pr_number: int | None = None
    pr_url: str | None = None
    results_json: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Submission":
        return cls(
            id=row["id"],
            workflow_run_id=row["workflow_run_id"],
            leaderboard_repo=row["leaderboard_repo"],
            purple_repo=row["purple_repo"],
            purple_owner=row["purple_owner"],
            status=row["status"],
            pr_number=row.get("pr_number"),
            pr_url=row.get("pr_url"),
            results_json=row.get("results_json"),
            error_message=row.get("error_message"),
            created_at=row.get("created_at"),
        )

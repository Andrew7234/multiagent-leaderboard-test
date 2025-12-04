"""Handle installation events - register leaderboards."""

from typing import Any

from github_client import get_repo_contents
from db import (
    get_leaderboard_by_repo_id,
    create_leaderboard,
    update_leaderboard_repo_name,
)
from handlers import Status


async def handle_installation(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle app installation on a repository."""
    
    action = payload.get("action")
    if action not in ("created", "added"):
        return {"status": Status.IGNORED, "reason": f"action={action}"}
    
    installation_id = payload["installation"]["id"]
    
    if "repositories" in payload:
        repos = payload["repositories"]
    elif "repositories_added" in payload:
        repos = payload["repositories_added"]
    else:
        return {"status": Status.IGNORED, "reason": "no repositories"}
    
    registered = []
    
    for repo in repos:
        if repo.get("fork", False):
            continue
        
        repo_full_name = repo["full_name"]
        repo_id = repo["id"]
        
        has_runner = await check_is_leaderboard(installation_id, repo_full_name)
        if not has_runner:
            continue
        
        existing = await get_leaderboard_by_repo_id(repo_id)
        
        if existing:
            if existing.repo_full_name != repo_full_name:
                await update_leaderboard_repo_name(repo_id, repo_full_name)
            continue
        
        await create_leaderboard(
            github_repo_id=repo_id,
            repo_full_name=repo_full_name,
            installation_id=installation_id,
        )
        registered.append(repo_full_name)
    
    return {"status": Status.OK, "registered": registered}


async def check_is_leaderboard(installation_id: int, repo_full_name: str) -> bool:
    """Check if repo has .github/workflows/runner.yml."""
    try:
        contents = await get_repo_contents(
            installation_id,
            repo_full_name,
            ".github/workflows/runner.yml"
        )
        return contents is not None
    except Exception:
        return False

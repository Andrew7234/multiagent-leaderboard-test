"""GitHub API client with installation token management."""

import time
from typing import Any

import httpx
import jwt

from config import settings

# Token cache: {installation_id: (token, expires_at)}
_token_cache: dict[int, tuple[str, float]] = {}


def generate_jwt() -> str:
    """Generate a JWT for GitHub App authentication."""
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": settings.app_id,
    }
    return jwt.encode(payload, settings.private_key, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    """Get or refresh an installation access token."""
    cached = _token_cache.get(installation_id)
    if cached and cached[1] > time.time() + 60:
        return cached[0]
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {generate_jwt()}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        
        token = data["token"]
        # Parse expires_at and cache
        _token_cache[installation_id] = (token, time.time() + 3500)
        return token


async def github_request(
    method: str,
    url: str,
    installation_id: int,
    **kwargs,
) -> Any:
    """Make an authenticated request to GitHub API."""
    token = await get_installation_token(installation_id)
    
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            f"https://api.github.com{url}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            **kwargs,
        )
        resp.raise_for_status()
        
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.content


async def get_repo_contents(installation_id: int, repo: str, path: str) -> dict | None:
    """Get file contents from a repository."""
    try:
        return await github_request("GET", f"/repos/{repo}/contents/{path}", installation_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


async def get_artifacts(installation_id: int, repo: str, run_id: int) -> dict:
    """List artifacts for a workflow run."""
    return await github_request("GET", f"/repos/{repo}/actions/runs/{run_id}/artifacts", installation_id)


async def download_artifact(installation_id: int, repo: str, artifact_id: int) -> bytes:
    """Download an artifact zip file."""
    return await github_request("GET", f"/repos/{repo}/actions/artifacts/{artifact_id}/zip", installation_id)


async def get_ref(installation_id: int, repo: str, ref: str) -> dict:
    """Get a git reference."""
    return await github_request("GET", f"/repos/{repo}/git/ref/heads/{ref}", installation_id)


async def create_branch(installation_id: int, repo: str, branch: str, from_ref: str):
    """Create a new branch."""
    ref_data = await get_ref(installation_id, repo, from_ref)
    sha = ref_data["object"]["sha"]
    
    try:
        await github_request(
            "POST",
            f"/repos/{repo}/git/refs",
            installation_id,
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 422:  # Already exists
            raise


async def commit_files(
    installation_id: int,
    repo: str,
    branch: str,
    files: dict[str, str],
    message: str,
):
    """Commit multiple files to a branch."""
    # Get current commit
    ref_data = await get_ref(installation_id, repo, branch)
    base_sha = ref_data["object"]["sha"]
    
    # Get base tree
    commit = await github_request("GET", f"/repos/{repo}/git/commits/{base_sha}", installation_id)
    base_tree_sha = commit["tree"]["sha"]
    
    # Create blobs and tree entries
    tree_entries = []
    for path, content in files.items():
        blob = await github_request(
            "POST",
            f"/repos/{repo}/git/blobs",
            installation_id,
            json={"content": content, "encoding": "utf-8"},
        )
        tree_entries.append({
            "path": path,
            "mode": "100644",
            "type": "blob",
            "sha": blob["sha"],
        })
    
    # Create tree
    tree = await github_request(
        "POST",
        f"/repos/{repo}/git/trees",
        installation_id,
        json={"base_tree": base_tree_sha, "tree": tree_entries},
    )
    
    # Create commit
    new_commit = await github_request(
        "POST",
        f"/repos/{repo}/git/commits",
        installation_id,
        json={
            "message": message,
            "tree": tree["sha"],
            "parents": [base_sha],
        },
    )
    
    # Update ref
    await github_request(
        "PATCH",
        f"/repos/{repo}/git/refs/heads/{branch}",
        installation_id,
        json={"sha": new_commit["sha"]},
    )


async def create_pull_request(
    installation_id: int,
    repo: str,
    head: str,
    base: str,
    title: str,
    body: str,
) -> dict:
    """Create a pull request."""
    return await github_request(
        "POST",
        f"/repos/{repo}/pulls",
        installation_id,
        json={"title": title, "body": body, "head": head, "base": base},
    )

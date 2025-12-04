"""Handle workflow_run events."""

import json
import zipfile
import io
from typing import Any

from models import Leaderboard
from db import (
    get_leaderboard_by_repo_name,
    get_submission_by_run_id,
    create_submission,
)
from github_client import (
    download_artifact,
    create_branch,
    commit_files,
    create_pull_request,
    get_artifacts,
)
from handlers import Status


async def handle_workflow_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle workflow_run.completed - submit results to leaderboard."""
    
    if payload.get("action") != "completed":
        return {"status": Status.IGNORED, "reason": "not completed"}
    
    run = payload["workflow_run"]
    
    if run.get("conclusion") != "success":
        return {"status": Status.IGNORED, "reason": f"conclusion={run.get('conclusion')}"}
    
    run_id = run["id"]
    purple_repo = payload["repository"]["full_name"]
    
    referenced = run.get("referenced_workflows", [])
    if not referenced:
        return {"status": Status.IGNORED, "reason": "no reusable workflows"}
    
    leaderboard = await find_leaderboard(referenced)
    if not leaderboard:
        return {"status": Status.IGNORED, "reason": "no registered leaderboard"}
    
    existing = await get_submission_by_run_id(run_id)
    if existing:
        return {"status": Status.IGNORED, "reason": "duplicate"}
    
    purple_installation_id = payload["installation"]["id"]
    artifact_data = await download_submission_artifact(purple_installation_id, purple_repo, run_id)
    
    if not artifact_data:
        await record_submission(run_id, leaderboard.repo_full_name, purple_repo, "failed", "No artifact found")
        return {"status": Status.ERROR, "reason": "no artifact"}
    
    results, manifest, scenario = parse_artifact(artifact_data)
    
    if manifest.get("target_leaderboard") != leaderboard.repo_full_name:
        await record_submission(run_id, leaderboard.repo_full_name, purple_repo, "rejected", "Target mismatch")
        return {"status": Status.REJECTED, "reason": "target mismatch"}
    
    pr_url = await create_submission_pr(
        leaderboard,
        manifest,
        results,
        scenario,
        run_id,
    )
    
    await record_submission(
        run_id,
        leaderboard.repo_full_name,
        purple_repo,
        "submitted",
        pr_url=pr_url,
        results=results,
    )
    
    return {"status": Status.OK, "pr_url": pr_url}


async def find_leaderboard(referenced_workflows: list[dict]) -> Leaderboard | None:
    """Find registered leaderboard from referenced workflows."""
    for ref in referenced_workflows:
        # ref["path"] = "owner/repo/.github/workflows/runner.yml"
        parts = ref["path"].split("/")
        if len(parts) < 2:
            continue
        repo_full_name = f"{parts[0]}/{parts[1]}"
        
        leaderboard = await get_leaderboard_by_repo_name(repo_full_name)
        if leaderboard:
            return leaderboard
    return None


async def download_submission_artifact(installation_id: int, repo: str, run_id: int) -> bytes | None:
    """Download the agentbeats-submission artifact."""
    artifacts = await get_artifacts(installation_id, repo, run_id)
    
    for artifact in artifacts.get("artifacts", []):
        if artifact["name"] == "agentbeats-submission":
            return await download_artifact(installation_id, repo, artifact["id"])
    
    return None


def parse_artifact(artifact_zip: bytes) -> tuple[dict, dict, str]:
    """Extract results.json, manifest.json, and scenario.toml from zip."""
    results = {}
    manifest = {}
    scenario = ""
    
    with zipfile.ZipFile(io.BytesIO(artifact_zip)) as zf:
        for name in zf.namelist():
            if name.endswith("results.json"):
                results = json.loads(zf.read(name))
            elif name.endswith("manifest.json"):
                manifest = json.loads(zf.read(name))
            elif name.endswith("scenario.toml"):
                scenario = zf.read(name).decode("utf-8")
    
    return results, manifest, scenario


async def create_submission_pr(
    leaderboard: Leaderboard,
    manifest: dict,
    results: dict,
    scenario: str,
    run_id: int,
) -> str:
    """Create a PR on the leaderboard with submission files."""
    
    purple_owner = manifest["purple_agent_owner"]
    timestamp = manifest["timestamp"].replace(":", "-").replace("T", "-")[:15]
    branch_name = f"agentbeats/submission-{run_id}"
    submission_path = f"submissions/{purple_owner}/{timestamp}"
    
    await create_branch(
        leaderboard.installation_id,
        leaderboard.repo_full_name,
        branch_name,
        "main",
    )
    
    files = {
        f"{submission_path}/results.json": json.dumps(results, indent=2),
        f"{submission_path}/manifest.json": json.dumps(manifest, indent=2),
        f"{submission_path}/scenario.toml": scenario,
    }
    
    await commit_files(
        leaderboard.installation_id,
        leaderboard.repo_full_name,
        branch_name,
        files,
        f"[AgentBeats] Submission from {purple_owner}",
    )
    
    pr = await create_pull_request(
        leaderboard.installation_id,
        leaderboard.repo_full_name,
        branch_name,
        "main",
        title=f"[Submission] {purple_owner}",
        body=format_pr_body(manifest, results),
    )
    
    return pr["html_url"]


def format_pr_body(manifest: dict, results: dict) -> str:
    """Generate PR body with submission details."""
    return f"""## AgentBeats Submission

| Field | Value |
|-------|-------|
| **Competitor** | @{manifest['purple_agent_owner']} |
| **Repository** | [{manifest['purple_agent_repo']}](https://github.com/{manifest['purple_agent_repo']}) |
| **Workflow Run** | [#{manifest['run_id']}]({manifest['run_url']}) |

### Results
```json
{json.dumps(results, indent=2)}
```

---
*Auto-generated by [AgentBeats](https://agentbeats.dev)*
"""


async def record_submission(
    run_id: int,
    leaderboard_repo: str,
    purple_repo: str,
    status: str,
    error: str = None,
    pr_url: str = None,
    results: dict = None,
):
    """Record submission in database."""
    await create_submission(
        workflow_run_id=run_id,
        leaderboard_repo=leaderboard_repo,
        purple_repo=purple_repo,
        purple_owner=purple_repo.split("/")[0],
        status=status,
        error_message=error,
        pr_url=pr_url,
        results_json=results,
    )

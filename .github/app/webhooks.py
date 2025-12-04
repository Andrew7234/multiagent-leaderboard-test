"""GitHub webhook handlers."""

from typing import Any

from handlers.installation import handle_installation
from handlers.workflow_run import handle_workflow_run


async def handle_webhook(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Route webhook to appropriate handler."""
    
    handlers = {
        "installation": handle_installation,
        "installation_repositories": handle_installation,
        "workflow_run": handle_workflow_run,
    }
    
    handler = handlers.get(event)
    if not handler:
        return {"status": "ignored", "event": event}
    
    return await handler(payload)

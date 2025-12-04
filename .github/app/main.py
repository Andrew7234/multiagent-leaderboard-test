"""AgentBeats GitHub App - Main entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

from webhooks import handle_webhook
from config import settings
from db import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="AgentBeats GitHub App",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/webhooks/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
):
    """Handle incoming GitHub webhooks."""
    body = await request.body()
    
    # TODO: Verify webhook signature
    # if not verify_signature(body, x_hub_signature_256, settings.webhook_secret):
    #     raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = await request.json()
    
    try:
        result = await handle_webhook(x_github_event, payload)
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        print(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

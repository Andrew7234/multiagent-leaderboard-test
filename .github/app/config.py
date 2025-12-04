"""Configuration settings."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from the app directory
load_dotenv(Path(__file__).parent / ".env")


@dataclass
class Settings:
    app_id: str = os.getenv("GITHUB_APP_ID", "")
    private_key: str = os.getenv("GITHUB_PRIVATE_KEY", "")
    webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    database_url: str = os.getenv("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/agentbeats")


settings = Settings()

"""
Environment variable management. Everything the app needs is read from .env
(copy .env.example to .env and fill it in).
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Anthropic / Claude
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

    # WhatsApp Cloud API (Meta) — from developers.facebook.com
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "changeme123")
    WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0")

    # Admin API protection (required for /businesses endpoints)
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

    # Database — SQLite for MVP, swap to Postgres URL in production
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./receptionist.db")

    APP_NAME = "AI Receptionist"


settings = Settings()

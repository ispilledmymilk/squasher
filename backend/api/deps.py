# backend/api/deps.py
"""FastAPI dependencies for production QA API."""

from typing import Optional

from fastapi import Header, HTTPException

from utils.config import config


async def verify_api_key(authorization: Optional[str] = Header(None)) -> None:
    """
    If API_SECRET_KEY is set, require Authorization: Bearer <token>.
    When unset, authentication is disabled (local dev only).
    """
    if not config.API_SECRET_KEY:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization[7:].strip()
    if token != config.API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def client_error_detail(message: str, exc: Exception) -> str:
    """Return safe error detail for HTTP responses."""
    if config.IS_PRODUCTION and not config.EXPOSE_ERROR_DETAILS:
        return message
    return f"{message}: {str(exc)}"

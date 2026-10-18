"""Reusable FastAPI dependencies: current user, current time, ownership checks."""
from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AuthSession, User
from app.security import hash_token


def get_now() -> datetime:
    """Injectable clock so tests can freeze time."""
    return datetime.now(timezone.utc)


def get_current_user(
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
    token: str | None = Cookie(default=None, alias=get_settings().cookie_name),
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if not token:
        raise unauthorized
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    if session is None or session.expires_at <= now:
        raise unauthorized
    user = db.get(User, session.user_id)
    if user is None:
        raise unauthorized
    return user


def get_owned(db: Session, model, obj_id: int, user: User, label: str):
    """Fetch a row only if it belongs to `user`. Otherwise 404 (never reveal that
    someone else's row exists). This is the defence against IDOR bugs."""
    obj = db.get(model, obj_id)
    if obj is None or obj.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} not found")
    return obj

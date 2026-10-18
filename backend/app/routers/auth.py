"""Register, log in, log out, current user."""
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user, get_now
from app.models import AuthSession, User
from app.schemas import LoginIn, RegisterIn, UserOut, UserUpdate
from app.security import hash_password, hash_token, new_session_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _start_session(db: Session, response: Response, user: User, now) -> None:
    token = new_session_token()
    db.add(AuthSession(user_id=user.id, token_hash=hash_token(token),
                       expires_at=now + timedelta(days=settings.session_expire_days)))
    db.commit()
    response.set_cookie(
        key=settings.cookie_name, value=token,
        max_age=settings.session_expire_days * 86400,
        httponly=True,  # JavaScript cannot read it (blocks token theft via XSS)
        secure=settings.cookie_secure,  # True in production (HTTPS only)
        samesite=settings.cookie_samesite,  # "lax": not sent on cross-site POSTs (CSRF defence)
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db), now=Depends(get_now)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=email, name=data.name, password_hash=hash_password(data.password),
                timezone=data.timezone or settings.default_timezone)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two simultaneous registrations
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    _start_session(db, response, user, now)
    return user


@router.post("/login", response_model=UserOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db), now=Depends(get_now)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not verify_password(data.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    _start_session(db, response, user, now)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=settings.cookie_name),
):
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == hash_token(token)))
        db.commit()
    response.delete_cookie(settings.cookie_name, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, key, value)
    db.commit()
    return user

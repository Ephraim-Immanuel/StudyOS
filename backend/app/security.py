"""Password hashing and session-token helpers."""
import hashlib
import secrets

import bcrypt

# Used to burn the same CPU time when the email is unknown (blunts timing attacks).
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    target = password_hash.encode("utf-8") if password_hash else _DUMMY_HASH
    ok = bcrypt.checkpw(password.encode("utf-8"), target)
    return ok and password_hash is not None


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

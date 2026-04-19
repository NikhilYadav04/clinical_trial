import os
import uuid
import json
import pathlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY         = os.getenv("JWT_SECRET", "trialmatch-dev-secret-change-in-prod")
ALGORITHM          = "HS256"
TOKEN_EXPIRE_DAYS  = 7

pwd_ctx      = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

DATA_DIR   = pathlib.Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load_users() -> list:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save_users(users: list) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")

def user_dir(user_id: str) -> pathlib.Path:
    d = DATA_DIR / "users" / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Password & token ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "email": email, "exp": expire},
                      SECRET_KEY, algorithm=ALGORITHM)


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise exc
    except JWTError:
        raise exc

    user = next((u for u in _load_users() if u["user_id"] == user_id), None)
    if not user:
        raise exc
    return user


# ── User CRUD ─────────────────────────────────────────────────────────────────

def find_by_email(email: str) -> Optional[dict]:
    return next((u for u in _load_users() if u["email"] == email.lower()), None)

def create_user(email: str, password: str, name: str) -> dict:
    users = _load_users()
    if any(u["email"] == email.lower() for u in users):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "user_id":       str(uuid.uuid4()),
        "email":         email.lower(),
        "name":          name.strip(),
        "password_hash": hash_password(password),
        "created_at":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    users.append(user)
    _save_users(users)
    user_dir(user["user_id"])      # create data directory
    return user

def public(user: dict) -> dict:
    return {k: user[k] for k in ("user_id", "email", "name", "created_at")}

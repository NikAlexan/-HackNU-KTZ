"""
POST /api/auth/login  — issue JWT
GET  /api/auth/me     — verify token & return user info
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 8

_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, _JWT_SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> str:
    """Decode JWT and return username. Raises HTTPException 401 on failure."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_ALGORITHM])
        username: str | None = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_user(
    creds: HTTPAuthorizationCredentials = Security(_bearer),
) -> str:
    """FastAPI dependency — validates Bearer JWT, returns username."""
    return decode_token(creds.credentials)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login")
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_token(user.username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(username: str = Depends(require_user)) -> dict:
    return {"username": username}

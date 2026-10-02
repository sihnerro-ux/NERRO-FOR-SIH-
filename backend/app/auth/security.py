from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Callable

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.domain.models import AuthUser, UserRole


JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-before-deployment")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))
password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def create_access_token(user: AuthUser) -> tuple[str, int]:
    expires = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    token = jwt.encode({"sub": user.id, "username": user.username, "role": user.role, "exp": expires}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, ACCESS_TOKEN_MINUTES * 60


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Authentication token is invalid or expired."}) from exc


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> AuthUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "Authentication is required."})
    payload = decode_access_token(credentials.credentials)
    from app.auth.service import auth_service
    user = auth_service.get_user(payload.get("sub", ""))
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "USER_NOT_FOUND", "message": "Authenticated user no longer exists."})
    return user


def require_roles(*roles: UserRole) -> Callable:
    def dependency(user: AuthUser = Depends(current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail={"code": "ROLE_FORBIDDEN", "message": "Your role cannot perform this action."})
        return user
    return dependency

"""Authentication dependencies and course-scoped authorization helpers."""

from __future__ import annotations

import secrets
from typing import Callable

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services.auth_service import get_session_user
from config import settings

SESSION_COOKIE_NAME = "courseagent_session"
CSRF_COOKIE_NAME = "courseagent_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"


def validate_request_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    trusted_origins = {item.rstrip("/") for item in settings.cors_origins if item != "*"}
    if not origin or origin.rstrip("/") not in trusted_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A trusted Origin is required.")


def csrf_rejection(request: Request) -> JSONResponse | None:
    """Reject unsafe cookie-authenticated requests without a trusted Origin and matching CSRF token."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None

    path = request.url.path
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    try:
        validate_request_origin(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    if session_token and path != "/api/auth/login":
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        csrf_header = request.headers.get(CSRF_HEADER_NAME)
        if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "A valid CSRF token is required."},
            )
    return None


class AuthenticatedUser(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str
    student_id: str | None = None
    course_scopes: list[str] = Field(default_factory=list)


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AuthenticatedUser:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign-in is required.")
    user = get_session_user(session_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired.")

    return AuthenticatedUser(**user)


def require_roles(*roles: str) -> Callable:
    allowed = {role.upper() for role in roles}

    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this operation.")
        return user

    return dependency


def require_course_access(user: AuthenticatedUser, course_id: str) -> None:
    if user.role == "ADMIN":
        return
    if user.role == "STUDENT":
        from app.data.db import get_db_connection

        with get_db_connection() as conn:
            enrolled = conn.execute(
                "SELECT 1 FROM students WHERE id = ? AND course_id = ?",
                (user.student_id, course_id),
            ).fetchone()
        if enrolled:
            return
    elif course_id in user.course_scopes:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course access is not authorized.")

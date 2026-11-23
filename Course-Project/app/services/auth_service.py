"""Database-backed password authentication and opaque server-side sessions."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.data.db import get_db_connection
from config import settings

_password_hasher = PasswordHasher()
_dummy_password_hash = _password_hasher.hash(secrets.token_urlsafe(32))
_MAX_FAILED_LOGINS = 5
_LOGIN_WINDOW = timedelta(minutes=15)
_LOGIN_LOCKOUT = timedelta(minutes=15)


class LoginRateLimitError(Exception):
    """Raised when an address exceeds the permitted failed-login attempts."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    if len(password) > 1024:
        raise ValueError("Password is too long.")
    return _password_hasher.hash(password)


def create_user(
    *,
    user_id: str,
    email: str,
    display_name: str,
    password: str,
    role: str,
    student_id: str | None = None,
    course_scopes: list[str] | None = None,
) -> None:
    normalized_role = role.strip().upper()
    if normalized_role not in {"STUDENT", "FACULTY", "ADMIN"}:
        raise ValueError("Role must be STUDENT, FACULTY, or ADMIN.")
    if not user_id.strip() or not display_name.strip():
        raise ValueError("User ID and display name are required.")
    if not email.strip() or "@" not in email:
        raise ValueError("A valid email address is required.")
    scopes = sorted({scope.strip() for scope in (course_scopes or []) if scope.strip()})
    if normalized_role == "STUDENT":
        if not student_id:
            raise ValueError("Student accounts must be linked to a student record.")
        if scopes:
            raise ValueError("Student course access is derived from enrollment.")
    elif student_id:
        raise ValueError("Only student accounts may be linked to a student record.")
    if normalized_role == "FACULTY" and not scopes:
        raise ValueError("Faculty accounts must be assigned at least one course scope.")
    if normalized_role == "ADMIN":
        scopes = []

    password_hash = hash_password(password)
    with get_db_connection(immediate=True) as conn:
        if normalized_role == "STUDENT":
            student = conn.execute(
                "SELECT id, course_id FROM students WHERE id = ?",
                (student_id,),
            ).fetchone()
            if not student:
                raise ValueError("Linked student record was not found.")
        conn.execute(
            """
            INSERT INTO auth_users
                (user_id, email, display_name, password_hash, role, student_id, course_scopes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id.strip(),
                email.strip().lower(),
                display_name.strip(),
                password_hash,
                normalized_role,
                student_id,
                json.dumps(scopes),
                _iso(_now()),
            ),
        )


def _address_key(remote_address: str) -> str:
    return hashlib.sha256(remote_address.encode("utf-8")).hexdigest()


def _check_login_limit(address_hash: str, now: datetime) -> None:
    with get_db_connection() as conn:
        record = conn.execute(
            "SELECT locked_until FROM auth_login_limits WHERE address_hash = ?",
            (address_hash,),
        ).fetchone()
    if record and record["locked_until"] and record["locked_until"] > _iso(now):
        raise LoginRateLimitError("Too many failed sign-in attempts. Try again later.")


def _record_login_failure(address_hash: str, now: datetime) -> None:
    now_iso = _iso(now)
    with get_db_connection(immediate=True) as conn:
        record = conn.execute(
            "SELECT window_started_at, failed_attempts FROM auth_login_limits WHERE address_hash = ?",
            (address_hash,),
        ).fetchone()
        if not record or _iso(datetime.fromisoformat(record["window_started_at"]) + _LOGIN_WINDOW) <= now_iso:
            conn.execute(
                """
                INSERT INTO auth_login_limits (address_hash, window_started_at, failed_attempts, locked_until)
                VALUES (?, ?, 1, NULL)
                ON CONFLICT(address_hash) DO UPDATE SET
                    window_started_at = excluded.window_started_at,
                    failed_attempts = 1,
                    locked_until = NULL
                """,
                (address_hash, now_iso),
            )
            return
        failures = int(record["failed_attempts"]) + 1
        locked_until = _iso(now + _LOGIN_LOCKOUT) if failures >= _MAX_FAILED_LOGINS else None
        conn.execute(
            """
            UPDATE auth_login_limits
            SET failed_attempts = ?, locked_until = ?
            WHERE address_hash = ?
            """,
            (failures, locked_until, address_hash),
        )


def authenticate(email: str, password: str, remote_address: str) -> tuple[dict[str, Any], str] | None:
    now = _now()
    address_hash = _address_key(remote_address)
    _check_login_limit(address_hash, now)
    normalized_email = email.strip().lower()
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM auth_users WHERE email = ?",
            (normalized_email,),
        ).fetchone()

    stored_hash = user["password_hash"] if user else _dummy_password_hash
    valid_password = False
    try:
        valid_password = _password_hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        valid_password = False

    if not user or not user["is_active"] or not valid_password:
        _record_login_failure(address_hash, now)
        return None

    if _password_hasher.check_needs_rehash(user["password_hash"]):
        upgraded_hash = _password_hasher.hash(password)
    else:
        upgraded_hash = user["password_hash"]

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    expires_at = _iso(now + timedelta(seconds=settings.auth_session_seconds))
    with get_db_connection(immediate=True) as conn:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (_iso(now),))
        conn.execute("DELETE FROM auth_login_limits WHERE address_hash = ?", (address_hash,))
        if upgraded_hash != user["password_hash"]:
            conn.execute(
                "UPDATE auth_users SET password_hash = ? WHERE user_id = ?",
                (upgraded_hash, user["user_id"]),
            )
        conn.execute(
            "INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash, user["user_id"], _iso(now), expires_at),
        )
    user_data = dict(user)
    user_data["course_scopes"] = json.loads(user_data["course_scopes"])
    return user_data, token


def get_session_user(token: str) -> dict[str, Any] | None:
    token_hash = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
    now_iso = _iso(_now())
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT u.user_id, u.email, u.display_name, u.role, u.student_id, u.course_scopes
            FROM auth_sessions s
            JOIN auth_users u ON u.user_id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ? AND u.is_active = 1
            """,
            (token_hash, now_iso),
        ).fetchone()
    if not row:
        return None
    user = dict(row)
    user["course_scopes"] = json.loads(user["course_scopes"])
    return user


def revoke_session(token: str) -> None:
    token_hash = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
    with get_db_connection(immediate=True) as conn:
        conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))

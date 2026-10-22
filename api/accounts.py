"""Optional account authentication and account-scoped assessment history.

Security model:
- Supabase Auth stores credentials and hashes passwords.
- The Flask API creates a random session token and stores only its SHA-256 hash.
- The token is delivered in a Secure, HttpOnly, SameSite=Lax cookie.
- Every history query is filtered by the session's user_id.
- New p2p_* tables have RLS enabled and no browser-facing policies.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import math
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from flask import Blueprint, jsonify, make_response, request
from werkzeug.exceptions import RequestEntityTooLarge

from src.config import CATEGORY_WEIGHTS
from src.readiness_scoring import ValidationError, assess
from src.recommendations import recommend, seven_day_plan
from .supabase_store import (
    SupabaseAuth,
    SupabaseError,
    SupabaseHTTPError,
    SupabaseRest,
    SupabaseUnavailable,
    auth_client,
    configured as supabase_configured,
    rest_client,
)

bp = Blueprint("accounts", __name__)
configured = supabase_configured
LOGGER = logging.getLogger(__name__)

SESSION_COOKIE = "p2p_session"
HOST_SESSION_COOKIE = "__Host-p2p_session"
SESSION_DAYS = 30
MAX_RECORDS = 200
NORMAL_BODY = 32 * 1024
IMPORT_BODY = 512 * 1024
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
ID_RE = re.compile(r"^[a-zA-Z0-9-]{10,80}$")
CATEGORY_NAMES = tuple(CATEGORY_WEIGHTS)
RATE_WINDOW = 15 * 60


class AccountError(Exception):
    def __init__(self, message: str, status: int = 400, code: str | None = None, *, retry_after: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.retry_after = retry_after


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_email(value: Any) -> str:
    if not isinstance(value, str):
        raise AccountError("Enter your email address.", 422, "invalid_email")
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise AccountError("Enter a valid email address.", 422, "invalid_email")
    return email


def validate_password(value: Any) -> str:
    if not isinstance(value, str):
        raise AccountError("Enter a password.", 422, "invalid_password")
    if len(value) < 8:
        raise AccountError("Use at least 8 characters for your password.", 422, "invalid_password")
    if len(value) > 128:
        raise AccountError("Use a password shorter than 129 characters.", 422, "invalid_password")
    if value.strip() == "":
        raise AccountError("Choose a password with visible characters.", 422, "invalid_password")
    return value


def validate_login_password(value: Any) -> str:
    # Existing shared-project accounts may predate this app's 8-character rule.
    if not isinstance(value, str) or not value:
        raise AccountError("Enter your password.", 422, "invalid_password")
    if len(value) > 128:
        raise AccountError("The password is too long.", 422, "invalid_password")
    return value


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_record(record: Any) -> bool:
    """Validate stored JSON before it is returned to a browser."""
    if not isinstance(record, dict):
        return False
    if not isinstance(record.get("id"), str) or not ID_RE.fullmatch(record["id"]):
        return False
    try:
        parse_timestamp(record.get("created_at"))
    except (ValueError, TypeError):
        return False
    if not isinstance(record.get("inputs"), dict) or not isinstance(record.get("band"), str):
        return False
    if not _is_number(record.get("score")) or not 0 <= record["score"] <= 100:
        return False
    if not isinstance(record.get("scoring_version"), str):
        return False
    categories = record.get("categories")
    if not isinstance(categories, dict) or set(categories) != set(CATEGORY_NAMES):
        return False
    if not all(_is_number(v) and 0 <= v <= 100 for v in categories.values()):
        return False
    missing = record.get("missing_optional")
    if not isinstance(missing, list) or not all(isinstance(v, str) for v in missing):
        return False
    recommendations = record.get("recommendations")
    if not isinstance(recommendations, list):
        return False
    for item in recommendations:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("title", "category", "reason", "task", "criterion", "priority")):
            return False
    plan = record.get("plan")
    if not isinstance(plan, list):
        return False
    for day in plan:
        if not isinstance(day, dict) or not isinstance(day.get("Day"), int) or not 1 <= day["Day"] <= 7:
            return False
        if not _is_number(day.get("Minutes")) or day["Minutes"] <= 0:
            return False
        if not all(isinstance(day.get(k), str) for k in ("Focus", "Task", "Done when")):
            return False
    return True


def _record(inputs: Any, record_id: str | None = None, created_at: Any = None) -> dict:
    if not isinstance(inputs, dict):
        raise AccountError("Assessment inputs must be an object.", 422, "invalid_inputs")
    try:
        result = assess(inputs)
    except ValidationError as exc:
        raise AccountError(str(exc), 422, "invalid_inputs") from None
    rid = record_id or secrets.token_hex(16)
    if not isinstance(rid, str) or not ID_RE.fullmatch(rid):
        raise AccountError("Choose a valid assessment identifier.", 422, "invalid_id")
    if created_at is None:
        stamp = utcnow()
    else:
        try:
            stamp = parse_timestamp(created_at)
        except (ValueError, TypeError):
            raise AccountError("A saved assessment has an invalid timestamp.", 422, "invalid_timestamp") from None
        if stamp < datetime(2020, 1, 1, tzinfo=timezone.utc) or stamp > utcnow() + timedelta(minutes=10):
            raise AccountError("A saved assessment timestamp is outside the supported range.", 422, "invalid_timestamp")
    return {
        **result,
        "id": rid,
        "created_at": iso(stamp),
        "recommendations": recommend(result["inputs"]),
        "plan": seven_day_plan(result["inputs"]),
    }


class SupabaseAccountStore:
    """Account persistence methods. Every account-data query includes user_id."""

    def __init__(self, rest: SupabaseRest):
        self.rest = rest

    def get_profile(self, user_id: str) -> dict | None:
        rows = self.rest.select(
            "p2p_profiles",
            {"user_id": f"eq.{user_id}", "select": "user_id,email,created_at", "limit": "1"},
        )
        return rows[0] if rows else None

    def upsert_profile(self, user_id: str, email: str) -> dict:
        rows = self.rest.insert(
            "p2p_profiles",
            [{"user_id": user_id, "email": email}],
            on_conflict="user_id",
            resolution="merge-duplicates",
        )
        if rows:
            return rows[0]
        mirrored = self.get_profile(user_id)
        if not mirrored:
            raise SupabaseUnavailable()
        return mirrored

    def delete_profile(self, user_id: str) -> int:
        return len(self.rest.delete("p2p_profiles", {"user_id": f"eq.{user_id}"}))

    def get_session(self, token_hash: str) -> dict | None:
        rows = self.rest.select(
            "p2p_sessions",
            {
                "token_hash": f"eq.{token_hash}",
                "expires_at": f"gt.{iso(utcnow())}",
                "select": "user_id,expires_at",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def create_session(self, token_hash: str, user_id: str, expires_at: datetime) -> bool:
        rows = self.rest.insert(
            "p2p_sessions",
            [{"token_hash": token_hash, "user_id": user_id, "expires_at": iso(expires_at)}],
            on_conflict="token_hash",
            resolution="ignore-duplicates",
        )
        return bool(rows)

    def delete_session(self, token_hash: str) -> None:
        self.rest.delete("p2p_sessions", {"token_hash": f"eq.{token_hash}"})

    def delete_expired_sessions(self, user_id: str) -> None:
        self.rest.delete(
            "p2p_sessions",
            {"user_id": f"eq.{user_id}", "expires_at": f"lt.{iso(utcnow())}"},
        )

    def delete_user_sessions(self, user_id: str, except_hash: str | None = None) -> None:
        params = {"user_id": f"eq.{user_id}"}
        if except_hash:
            params["token_hash"] = f"neq.{except_hash}"
        self.rest.delete("p2p_sessions", params)

    def list_assessments(self, user_id: str) -> list[dict]:
        rows = self.rest.select(
            "p2p_assessments",
            {
                "user_id": f"eq.{user_id}",
                "select": "id,record,created_at",
                "order": "created_at.asc",
                "limit": str(MAX_RECORDS),
            },
        )
        return [row.get("record") for row in rows if isinstance(row, dict)]

    def get_assessment(self, user_id: str, assessment_id: str) -> dict | None:
        rows = self.rest.select(
            "p2p_assessments",
            {
                "user_id": f"eq.{user_id}",
                "id": f"eq.{assessment_id}",
                "select": "record",
                "limit": "1",
            },
        )
        return rows[0].get("record") if rows and isinstance(rows[0], dict) else None

    def count_assessments(self, user_id: str) -> int:
        return self.rest.count("p2p_assessments", {"user_id": f"eq.{user_id}"})

    def insert_assessments(self, rows: list[dict]) -> list[dict]:
        if not rows:
            return []
        return self.rest.insert(
            "p2p_assessments",
            rows,
            on_conflict="user_id,id",
            resolution="ignore-duplicates",
        )

    def delete_assessment(self, user_id: str, assessment_id: str) -> int:
        return len(
            self.rest.delete(
                "p2p_assessments",
                {"user_id": f"eq.{user_id}", "id": f"eq.{assessment_id}"},
            )
        )

    def delete_all_assessments(self, user_id: str) -> int:
        return len(self.rest.delete("p2p_assessments", {"user_id": f"eq.{user_id}"}))

    def get_attempt(self, key_hash: str) -> dict | None:
        rows = self.rest.select(
            "p2p_auth_attempts",
            {"key_hash": f"eq.{key_hash}", "select": "attempts,window_started_at", "limit": "1"},
        )
        return rows[0] if rows else None

    def save_attempt(self, key_hash: str, attempts: int, window_started_at: datetime) -> None:
        self.rest.insert(
            "p2p_auth_attempts",
            [{"key_hash": key_hash, "attempts": attempts, "window_started_at": iso(window_started_at)}],
            on_conflict="key_hash",
            resolution="merge-duplicates",
        )

    def delete_attempt(self, key_hash: str) -> None:
        self.rest.delete("p2p_auth_attempts", {"key_hash": f"eq.{key_hash}"})


class AccountService:
    def __init__(self, store: Any, auth: Any, rate_secret: str | None = None):
        self.store = store
        self.auth = auth
        self.rate_secret = (
            rate_secret or os.environ.get("SUPABASE_SECRET_KEY") or secrets.token_hex(32)
        ).encode("utf-8")

    def _rate_key(self, kind: str, value: str) -> str:
        return hmac.new(self.rate_secret, f"{kind}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()

    def _limits(self, email: str, ip: str) -> list[tuple[str, str, int, int]]:
        return [
            ("login-email", email, 8, RATE_WINDOW),
            ("login-ip", ip, 30, RATE_WINDOW),
        ]

    def _check_limits(self, specs: list[tuple[str, str, int, int]]) -> None:
        now = utcnow()
        for kind, value, maximum, seconds in specs:
            key = self._rate_key(kind, value)
            row = self.store.get_attempt(key)
            if not row:
                continue
            try:
                started = parse_timestamp(row.get("window_started_at"))
                attempts = int(row.get("attempts") or 0)
            except (ValueError, TypeError):
                continue
            if now - started < timedelta(seconds=seconds) and attempts >= maximum:
                raise AccountError(
                    "Too many attempts. Wait a few minutes and try again.",
                    429,
                    "rate_limited",
                    retry_after=seconds,
                )

    def _record_attempts(self, specs: list[tuple[str, str, int, int]]) -> None:
        now = utcnow()
        for kind, value, _maximum, seconds in specs:
            key = self._rate_key(kind, value)
            row = self.store.get_attempt(key)
            attempts = 1
            started = now
            if row:
                try:
                    previous_start = parse_timestamp(row.get("window_started_at"))
                    if now - previous_start < timedelta(seconds=seconds):
                        attempts = int(row.get("attempts") or 0) + 1
                        started = previous_start
                except (ValueError, TypeError):
                    pass
            self.store.save_attempt(key, attempts, started)

    def _clear_limits(self, specs: list[tuple[str, str, int, int]]) -> None:
        for kind, value, _maximum, _seconds in specs:
            self.store.delete_attempt(self._rate_key(kind, value))

    def _new_session(self, user_id: str) -> str:
        self.store.delete_expired_sessions(user_id)
        expires = utcnow() + timedelta(days=SESSION_DAYS)
        for _ in range(2):
            token = secrets.token_urlsafe(32)
            if self.store.create_session(_token_hash(token), user_id, expires):
                return token
        raise SupabaseUnavailable()

    @staticmethod
    def public_user(profile: dict, session: dict) -> dict:
        return {
            "email": profile.get("email", ""),
            "member_since": profile.get("created_at"),
            "session_expires_at": session.get("expires_at"),
            "assessment_limit": MAX_RECORDS,
        }

    def session_for(self, token: str | None) -> dict | None:
        if not token or len(token) > 200:
            return None
        token_hash = _token_hash(token)
        row = self.store.get_session(token_hash)
        if not row:
            return None
        user_id = row.get("user_id")
        profile = self.store.get_profile(user_id) if isinstance(user_id, str) else None
        if not profile:
            self.store.delete_session(token_hash)
            return None
        return {
            "user_id": user_id,
            "email": profile.get("email", ""),
            "member_since": profile.get("created_at"),
            "expires_at": row.get("expires_at"),
            "token_hash": token_hash,
        }

    def signup(self, email: str, password: str, ip: str) -> tuple[dict, str]:
        email = normalize_email(email)
        password = validate_password(password)
        signup_limits = [("signup-ip", ip, 5, 60 * 60)]
        self._check_limits(signup_limits)
        self._record_attempts(signup_limits)
        try:
            user = self.auth.create_user(email, password)
        except SupabaseHTTPError as exc:
            if exc.status in (409, 422) or (exc.code or "").lower() in (
                "email_exists",
                "user_already_exists",
            ) or "already" in exc.message.lower():
                raise AccountError(
                    "An account with this email already exists. Sign in instead.",
                    409,
                    "email_exists",
                ) from None
            if exc.status == 429:
                raise AccountError(
                    "Too many sign-up attempts. Please wait and try again.",
                    429,
                    "rate_limited",
                ) from None
            raise AccountError(
                "We couldn’t create that account. Check your details and try again.",
                400,
                "signup_failed",
            ) from None
        try:
            self.auth.login(email, password)
        except SupabaseError as exc:
            try:
                self.auth.delete_user(str(user["id"]))
            except SupabaseError:
                pass
            if isinstance(exc, SupabaseHTTPError) and exc.status == 429:
                raise AccountError("Too many attempts. Please wait and try again.", 429, "rate_limited") from None
            raise AccountError(
                "Your account could not be activated automatically. Try signing in.",
                503,
                "signup_activation_failed",
            ) from None
        profile = self.store.upsert_profile(str(user["id"]), email)
        session = {"expires_at": iso(utcnow() + timedelta(days=SESSION_DAYS))}
        token = self._new_session(str(user["id"]))
        return self.public_user(profile, session), token

    def login(self, email: str, password: str, ip: str) -> tuple[dict, str]:
        email = normalize_email(email)
        password = validate_login_password(password)
        limits = self._limits(email, ip)
        self._check_limits(limits)
        try:
            user = self.auth.login(email, password)
        except SupabaseHTTPError as exc:
            code = (exc.code or "").lower()
            if code == "email_not_confirmed" or "confirm" in exc.message.lower():
                raise AccountError(
                    "This email needs confirmation before it can sign in.",
                    403,
                    "email_not_confirmed",
                ) from None
            if exc.status in (400, 401) or code in ("invalid_credentials", "invalid_grant"):
                self._record_attempts(limits)
                raise AccountError("Email or password is incorrect.", 401, "invalid_credentials") from None
            if exc.status == 429:
                raise AccountError(
                    "Too many sign-in attempts. Please wait and try again.",
                    429,
                    "rate_limited",
                ) from None
            raise AccountError(
                "Accounts are temporarily unavailable. Your browser assessment still works.",
                503,
                "accounts_unavailable",
            ) from None
        self._clear_limits(limits)
        profile = self.store.upsert_profile(str(user["id"]), email)
        session = {"expires_at": iso(utcnow() + timedelta(days=SESSION_DAYS))}
        token = self._new_session(str(user["id"]))
        return self.public_user(profile, session), token

    def logout(self, token_hash: str | None) -> None:
        if token_hash:
            self.store.delete_session(token_hash)

    def list_history(self, user_id: str) -> tuple[list[dict], int]:
        records = []
        skipped = 0
        for record in self.store.list_assessments(user_id):
            if valid_record(record):
                records.append(record)
            else:
                skipped += 1
        return records, skipped

    def save_history(self, user_id: str, inputs: Any, record_id: str | None = None) -> tuple[dict, bool]:
        if record_id and (not isinstance(record_id, str) or not ID_RE.fullmatch(record_id)):
            raise AccountError("Choose a valid assessment identifier.", 422, "invalid_id")
        if record_id:
            existing = self.store.get_assessment(user_id, record_id)
            if existing and valid_record(existing):
                return existing, False
        if self.store.count_assessments(user_id) >= MAX_RECORDS:
            raise AccountError(
                f"Your account has {MAX_RECORDS} saved assessments. Delete some before saving more.",
                409,
                "history_full",
            )
        record = _record(inputs, record_id)
        inserted = self.store.insert_assessments(
            [
                {
                    "id": record["id"],
                    "user_id": user_id,
                    "record": record,
                    "created_at": record["created_at"],
                }
            ]
        )
        if not inserted:
            existing = self.store.get_assessment(user_id, record["id"])
            if existing and valid_record(existing):
                return existing, False
            raise SupabaseUnavailable()
        return record, True

    def import_history(self, user_id: str, items: Any) -> tuple[list[dict], int, int]:
        if not isinstance(items, list) or not items:
            raise AccountError("Choose a backup containing at least one assessment.", 422, "invalid_backup")
        if len(items) > MAX_RECORDS:
            raise AccountError(f"A single import is limited to {MAX_RECORDS} assessments.", 422, "too_many")
        ids: set[str] = set()
        prepared: list[dict] = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise AccountError(f"Assessment {index + 1} is not a valid record.", 422, "invalid_backup")
            inputs = item.get("inputs")
            record_id = item.get("id")
            if not isinstance(record_id, str) or not ID_RE.fullmatch(record_id):
                raise AccountError(f"Assessment {index + 1} has an invalid identifier.", 422, "invalid_backup")
            if record_id in ids:
                raise AccountError("This backup contains duplicate assessment identifiers.", 422, "duplicate_id")
            ids.add(record_id)
            try:
                prepared.append(_record(inputs, record_id, item.get("created_at")))
            except AccountError as exc:
                raise AccountError(f"Assessment {index + 1}: {exc.message}", 422, "invalid_backup") from None
        existing = {record.get("id") for record in self.store.list_assessments(user_id) if isinstance(record, dict)}
        new_items = [record for record in prepared if record["id"] not in existing]
        if self.store.count_assessments(user_id) + len(new_items) > MAX_RECORDS:
            raise AccountError(
                f"This import would exceed the {MAX_RECORDS}-assessment account limit.",
                409,
                "history_full",
            )
        rows = [
            {
                "id": record["id"],
                "user_id": user_id,
                "record": record,
                "created_at": record["created_at"],
            }
            for record in new_items
        ]
        inserted = self.store.insert_assessments(rows)
        records, _skipped = self.list_history(user_id)
        return records, len(inserted), len(prepared) - len(inserted)

    def delete_history_item(self, user_id: str, assessment_id: str) -> None:
        if not ID_RE.fullmatch(assessment_id or ""):
            raise AccountError("Assessment not found.", 404, "not_found")
        if self.store.delete_assessment(user_id, assessment_id) == 0:
            raise AccountError("Assessment not found.", 404, "not_found")

    def clear_history(self, user_id: str) -> None:
        self.store.delete_all_assessments(user_id)

    def delete_account_data(self, user_id: str) -> None:
        self.store.delete_profile(user_id)

    def change_password(self, session: dict, current_password: str, new_password: str, ip: str) -> None:
        email = session["email"]
        new_password = validate_password(new_password)
        limits = self._limits(email, ip)
        self._check_limits(limits)
        try:
            self.auth.login(email, current_password)
        except SupabaseHTTPError as exc:
            if exc.status in (400, 401) or (exc.code or "").lower() in ("invalid_credentials", "invalid_grant"):
                self._record_attempts(limits)
                raise AccountError("Your current password is incorrect.", 401, "invalid_credentials") from None
            if exc.status == 429:
                raise AccountError("Too many attempts. Please wait and try again.", 429, "rate_limited") from None
            raise AccountError("Accounts are temporarily unavailable.", 503, "accounts_unavailable") from None
        self._clear_limits(limits)
        try:
            self.auth.update_password(session["user_id"], new_password)
        except SupabaseHTTPError:
            raise AccountError(
                "Your password could not be changed. Try again or contact the site owner.",
                503,
                "password_update_failed",
            ) from None
        self.store.delete_user_sessions(session["user_id"], except_hash=session["token_hash"])


def get_service() -> AccountService:
    if not supabase_configured():
        raise SupabaseUnavailable()
    return AccountService(SupabaseAccountStore(rest_client()), auth_client())


def _body(max_bytes: int) -> dict:
    if request.content_length and request.content_length > max_bytes:
        raise RequestEntityTooLarge()
    if not request.is_json:
        raise AccountError("Send JSON with this request.", 415, "json_required")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise AccountError("Send a JSON object.", 400, "invalid_json")
    return data


def _secure_cookie() -> bool:
    proto = (request.headers.get("x-forwarded-proto") or request.scheme).split(",")[0].strip().lower()
    host = (request.host or "").split(":")[0].lower()
    return proto == "https" and host not in ("localhost", "127.0.0.1")


def _cookie_name() -> str:
    return HOST_SESSION_COOKIE if _secure_cookie() else SESSION_COOKIE


def _token_from_request() -> str | None:
    return request.cookies.get(_cookie_name()) or request.cookies.get(
        SESSION_COOKIE if _cookie_name() == HOST_SESSION_COOKIE else HOST_SESSION_COOKIE
    )


def _set_session_cookie(response, token: str):
    secure = _secure_cookie()
    response.set_cookie(
        HOST_SESSION_COOKIE if secure else SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="Lax",
        path="/",
    )
    return response


def _clear_session_cookie(response):
    for name, secure in ((HOST_SESSION_COOKIE, True), (SESSION_COOKIE, False)):
        response.delete_cookie(name, path="/", secure=secure, httponly=True, samesite="Lax")
    return response


def client_ip() -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    return (forwarded or request.remote_addr or "unknown")[:64]


def _require_session(service: AccountService) -> dict:
    session = service.session_for(_token_from_request())
    if not session:
        raise AccountError("Sign in to use your account.", 401, "not_signed_in")
    return session


@bp.before_request
def same_origin_only():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None
    origin = request.headers.get("Origin")
    host = (request.host or "").split(":")[0].lower()
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() != host:
            return jsonify(error="This request did not come from this site."), 403
    site = request.headers.get("Sec-Fetch-Site")
    if site and site not in ("same-origin", "none"):
        return jsonify(error="This request did not come from this site."), 403
    return None


@bp.errorhandler(AccountError)
def account_error(exc: AccountError):
    response = jsonify(error=exc.message, code=exc.code)
    response.status_code = exc.status
    if exc.retry_after:
        response.headers["Retry-After"] = str(exc.retry_after)
    return response


@bp.errorhandler(SupabaseError)
def backend_error(exc: SupabaseError):
    LOGGER.warning("Account backend request failed: %s", exc.__class__.__name__)
    return (
        jsonify(
            error="Accounts are temporarily unavailable. Your browser assessment still works.",
            code="accounts_unavailable",
        ),
        503,
    )


@bp.get("/api/auth/me")
def me():
    if not supabase_configured():
        return jsonify(available=False, user=None)
    try:
        service = get_service()
    except SupabaseUnavailable:
        return jsonify(available=False, user=None, error="Accounts are temporarily unavailable."), 503
    try:
        session = service.session_for(_token_from_request())
        if not session:
            response = jsonify(available=True, user=None)
            return _clear_session_cookie(response) if request.cookies else response
        profile = {"email": session["email"], "created_at": session["member_since"]}
        return jsonify(available=True, user=service.public_user(profile, {"expires_at": session["expires_at"]}))
    except SupabaseUnavailable:
        return jsonify(available=False, user=None, error="Accounts are temporarily unavailable."), 503


@bp.post("/api/auth/signup")
def signup():
    body = _body(NORMAL_BODY)
    service = get_service()
    user, token = service.signup(body.get("email"), body.get("password"), client_ip())
    response = jsonify(available=True, user=user)
    response.status_code = 201
    return _set_session_cookie(response, token)


@bp.post("/api/auth/login")
def login():
    body = _body(NORMAL_BODY)
    service = get_service()
    user, token = service.login(body.get("email"), body.get("password"), client_ip())
    return _set_session_cookie(jsonify(available=True, user=user), token)


@bp.post("/api/auth/logout")
def logout():
    try:
        service = get_service()
        token = _token_from_request()
        service.logout(_token_hash(token) if token else None)
    except SupabaseUnavailable:
        pass
    return _clear_session_cookie(make_response("", 204))


@bp.post("/api/auth/password")
def password():
    body = _body(NORMAL_BODY)
    service = get_service()
    session = _require_session(service)
    service.change_password(
        session,
        body.get("current_password"),
        body.get("new_password"),
        client_ip(),
    )
    return jsonify(message="Password changed. Other sessions have been signed out.")


@bp.get("/api/history")
def history():
    service = get_service()
    session = _require_session(service)
    records, skipped = service.list_history(session["user_id"])
    return jsonify(assessments=records, limit=MAX_RECORDS, skipped=skipped, synced=True)


@bp.post("/api/history")
def save_history():
    body = _body(NORMAL_BODY)
    service = get_service()
    session = _require_session(service)
    record, created = service.save_history(session["user_id"], body.get("inputs"), body.get("id"))
    response = jsonify(record=record, created=created)
    response.status_code = 201 if created else 200
    return response


@bp.post("/api/history/import")
def import_history():
    body = _body(IMPORT_BODY)
    service = get_service()
    session = _require_session(service)
    records, imported, skipped = service.import_history(session["user_id"], body.get("items"))
    return jsonify(
        assessments=records,
        imported=imported,
        skipped_existing=skipped,
        limit=MAX_RECORDS,
        synced=True,
    )


@bp.delete("/api/history/<assessment_id>")
def delete_history(assessment_id: str):
    service = get_service()
    session = _require_session(service)
    service.delete_history_item(session["user_id"], assessment_id)
    return make_response("", 204)


@bp.delete("/api/history")
def clear_history():
    service = get_service()
    session = _require_session(service)
    service.clear_history(session["user_id"])
    return make_response("", 204)


@bp.delete("/api/account/data")
def delete_account_data():
    service = get_service()
    session = _require_session(service)
    service.delete_account_data(session["user_id"])
    return _clear_session_cookie(make_response("", 204))

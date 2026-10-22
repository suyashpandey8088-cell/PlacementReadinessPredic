"""Minimal server-only Supabase REST/Auth client.

The browser never receives these credentials. The Flask API calls Supabase with
the server secret key and always scopes account data by the authenticated user.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class SupabaseError(Exception):
    """Base error with a safe, user-facing message."""

    def __init__(self, message: str, status: int = 503, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


class SupabaseUnavailable(SupabaseError):
    """The hosted account service could not be reached."""

    def __init__(self):
        super().__init__(
            "Accounts are temporarily unavailable. Your browser assessment still works.",
            503,
            "accounts_unavailable",
        )


class SupabaseHTTPError(SupabaseError):
    """A non-2xx response from Supabase. Raw provider messages stay server-side."""


def _settings() -> tuple[str, str, str]:
    url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    secret = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()
    publishable = (os.environ.get("SUPABASE_PUBLISHABLE_KEY") or "").strip()
    return url, secret, publishable


def configured() -> bool:
    url, secret, publishable = _settings()
    return bool(url.startswith(("https://", "http://")) and secret and publishable)


def _decode(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _key_headers(key: str) -> dict[str, str]:
    """New sb_ keys use apikey only; legacy service_role JWTs also need Bearer."""
    headers = {"apikey": key, "Accept": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _call(
    method: str,
    url: str,
    key: str,
    *,
    body: Any = None,
    headers: dict[str, str] | None = None,
    timeout: int = 12,
) -> tuple[dict[str, str], Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {**_key_headers(key), "User-Agent": "Path2Placement/2.0"}
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url, data=payload, method=method, headers=request_headers
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return {k.lower(): v for k, v in response.headers.items()}, _decode(raw)
    except urllib.error.HTTPError as exc:
        data = _decode(exc.read())
        message = "The account service rejected this request."
        code = None
        if isinstance(data, dict):
            message = str(
                data.get("message") or data.get("error_description") or data.get("error") or message
            )
            code = data.get("error_code") or data.get("code")
        raise SupabaseHTTPError(message[:300], exc.code, code) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise SupabaseUnavailable() from None


class SupabaseRest:
    """Small PostgREST wrapper. Account tables have RLS enabled with no policies."""

    def __init__(self, url: str, secret: str):
        self.url = url
        self.secret = secret

    def _url(self, table: str, params: dict[str, str] | None = None) -> str:
        url = f"{self.url}/rest/v1/{urllib.parse.quote(table)}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        return url

    def select(self, table: str, params: dict[str, str] | None = None) -> list[dict]:
        _, data = _call("GET", self._url(table, params), self.secret)
        return data if isinstance(data, list) else []

    def count(self, table: str, params: dict[str, str] | None = None) -> int:
        query = dict(params or {})
        query.update({"select": "id", "limit": "1"})
        headers, _ = _call(
            "GET",
            self._url(table, query),
            self.secret,
            headers={"Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
        )
        content_range = headers.get("content-range", "")
        try:
            return int(content_range.rsplit("/", 1)[1])
        except (IndexError, ValueError):
            return 0

    def insert(
        self,
        table: str,
        rows: list[dict],
        *,
        on_conflict: str | None = None,
        resolution: str | None = None,
    ) -> list[dict]:
        params = {"on_conflict": on_conflict} if on_conflict else None
        prefer = "return=representation"
        if resolution:
            prefer = f"{prefer},resolution={resolution}"
        _, data = _call(
            "POST",
            self._url(table, params),
            self.secret,
            body=rows,
            headers={"Prefer": prefer},
        )
        return data if isinstance(data, list) else []

    def update(self, table: str, params: dict[str, str], values: dict) -> list[dict]:
        _, data = _call(
            "PATCH",
            self._url(table, params),
            self.secret,
            body=values,
            headers={"Prefer": "return=representation"},
        )
        return data if isinstance(data, list) else []

    def delete(self, table: str, params: dict[str, str]) -> list[dict]:
        _, data = _call(
            "DELETE",
            self._url(table, params),
            self.secret,
            headers={"Prefer": "return=representation"},
        )
        return data if isinstance(data, list) else []


class SupabaseAuth:
    """GoTrue admin and password endpoints, called only from the API."""

    def __init__(self, url: str, secret: str, publishable: str):
        self.url = url
        self.secret = secret
        self.publishable = publishable

    def _call(self, method: str, path: str, *, body: Any = None, admin: bool) -> Any:
        key = self.secret if admin else self.publishable
        headers, data = _call(
            method,
            f"{self.url}/auth/v1/{path}",
            key,
            body=body,
            headers={"Content-Type": "application/json"},
        )
        return data

    def create_user(self, email: str, password: str) -> dict:
        data = self._call(
            "POST",
            "admin/users",
            body={"email": email, "password": password, "email_confirm": True},
            admin=True,
        )
        if not isinstance(data, dict) or not data.get("id"):
            raise SupabaseHTTPError("Account creation did not return a user.", 502)
        return data

    def delete_user(self, user_id: str) -> None:
        self._call("DELETE", f"admin/users/{user_id}", admin=True)

    def login(self, email: str, password: str) -> dict:
        data = self._call(
            "POST",
            "token?grant_type=password",
            body={"email": email, "password": password},
            admin=False,
        )
        user = data.get("user") if isinstance(data, dict) else None
        if not isinstance(user, dict) or not user.get("id"):
            raise SupabaseHTTPError("Sign-in did not return a user.", 502)
        return user

    def update_password(self, user_id: str, password: str) -> dict:
        data = self._call(
            "PUT",
            f"admin/users/{user_id}",
            body={"password": password},
            admin=True,
        )
        return data if isinstance(data, dict) else {}


def rest_client() -> SupabaseRest:
    url, secret, _ = _settings()
    if not configured():
        raise SupabaseUnavailable()
    return SupabaseRest(url, secret)


def auth_client() -> SupabaseAuth:
    url, secret, publishable = _settings()
    if not configured():
        raise SupabaseUnavailable()
    return SupabaseAuth(url, secret, publishable)

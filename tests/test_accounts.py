import uuid
from datetime import datetime, timedelta, timezone

import pytest

from api import accounts
from api.accounts import AccountError, AccountService, _record, valid_record
from api.supabase_store import SupabaseHTTPError
from src.config import FIELDS

PASSWORD = "correct horse battery"


def assessment_inputs():
    return {key: spec[3] for key, spec in FIELDS.items()}


class FakeAuth:
    def __init__(self):
        self.users = {}

    def create_user(self, email, password):
        if email in self.users:
            raise SupabaseHTTPError("already registered", 422, "email_exists")
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "password": password,
            "confirmed": True,
        }
        self.users[email] = user
        return user

    def delete_user(self, user_id):
        for email, user in list(self.users.items()):
            if user["id"] == user_id:
                del self.users[email]

    def login(self, email, password):
        user = self.users.get(email)
        if not user or user["password"] != password:
            raise SupabaseHTTPError("Invalid login credentials", 400, "invalid_grant")
        return {"id": user["id"], "email": email}

    def update_password(self, user_id, password):
        for user in self.users.values():
            if user["id"] == user_id:
                user["password"] = password
                return {"id": user_id, "email": user["email"]}
        raise SupabaseHTTPError("missing", 404, "not_found")


class FakeStore:
    def __init__(self):
        self.profiles = {}
        self.sessions = {}
        self.assessments = []
        self.attempts = {}

    def now(self):
        return datetime.now(timezone.utc)

    def get_profile(self, user_id):
        return self.profiles.get(user_id)

    def upsert_profile(self, user_id, email):
        if user_id not in self.profiles:
            self.profiles[user_id] = {
                "user_id": user_id,
                "email": email,
                "created_at": self.now().isoformat(),
            }
        else:
            self.profiles[user_id]["email"] = email
        return dict(self.profiles[user_id])

    def delete_profile(self, user_id):
        if user_id not in self.profiles:
            return 0
        del self.profiles[user_id]
        self.sessions = {k: v for k, v in self.sessions.items() if v["user_id"] != user_id}
        self.assessments = [r for r in self.assessments if r["user_id"] != user_id]
        return 1

    def get_session(self, token_hash):
        session = self.sessions.get(token_hash)
        if not session:
            return None
        if session["expires_at"] <= self.now():
            del self.sessions[token_hash]
            return None
        return {"user_id": session["user_id"], "expires_at": session["expires_at"].isoformat()}

    def create_session(self, token_hash, user_id, expires_at):
        if token_hash in self.sessions:
            return False
        self.sessions[token_hash] = {"user_id": user_id, "expires_at": expires_at}
        return True

    def delete_session(self, token_hash):
        self.sessions.pop(token_hash, None)

    def delete_expired_sessions(self, user_id):
        now = self.now()
        self.sessions = {
            k: v for k, v in self.sessions.items() if not (v["user_id"] == user_id and v["expires_at"] <= now)
        }

    def delete_user_sessions(self, user_id, except_hash=None):
        self.sessions = {
            k: v
            for k, v in self.sessions.items()
            if not (v["user_id"] == user_id and k != except_hash)
        }

    def list_assessments(self, user_id):
        rows = [r for r in self.assessments if r["user_id"] == user_id]
        rows.sort(key=lambda r: r["created_at"])
        return [r["record"] for r in rows]

    def get_assessment(self, user_id, assessment_id):
        for row in self.assessments:
            if row["user_id"] == user_id and row["id"] == assessment_id:
                return row["record"]
        return None

    def count_assessments(self, user_id):
        return sum(1 for r in self.assessments if r["user_id"] == user_id)

    def insert_assessments(self, rows):
        inserted = []
        for row in rows:
            if any(
                existing["user_id"] == row["user_id"] and existing["id"] == row["id"]
                for existing in self.assessments
            ):
                continue
            self.assessments.append({**row})
            inserted.append(row)
        return inserted

    def delete_assessment(self, user_id, assessment_id):
        before = len(self.assessments)
        self.assessments = [
            r for r in self.assessments if not (r["user_id"] == user_id and r["id"] == assessment_id)
        ]
        return before - len(self.assessments)

    def delete_all_assessments(self, user_id):
        before = len(self.assessments)
        self.assessments = [r for r in self.assessments if r["user_id"] != user_id]
        return before - len(self.assessments)

    def get_attempt(self, key_hash):
        return self.attempts.get(key_hash)

    def save_attempt(self, key_hash, attempts, window_started_at):
        self.attempts[key_hash] = {
            "attempts": attempts,
            "window_started_at": window_started_at.isoformat(),
        }

    def delete_attempt(self, key_hash):
        self.attempts.pop(key_hash, None)


@pytest.fixture
def service():
    store = FakeStore()
    auth = FakeAuth()
    return AccountService(store, auth, rate_secret="test-rate-secret"), store, auth


@pytest.fixture
def configured_client(monkeypatch, service):
    from api.index import app

    app.config["TESTING"] = True
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    monkeypatch.setattr(accounts, "get_service", lambda: service[0])
    return app.test_client()


def signup(client, email="student@example.com", ip="203.0.113.10"):
    return client.post(
        "/api/auth/signup",
        json={"email": email, "password": PASSWORD},
        environ_base={"REMOTE_ADDR": ip},
    )


def login(client, email="student@example.com", password=PASSWORD, ip="203.0.113.10"):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        environ_base={"REMOTE_ADDR": ip},
    )


def test_health_and_unconfigured_auth(monkeypatch):
    from api.index import app

    app.config["TESTING"] = True
    for key in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_PUBLISHABLE_KEY"):
        monkeypatch.delenv(key, raising=False)
    client = app.test_client()
    health = client.get("/api/health").json
    assert health["history"] == "browser-or-account"
    assert health["auth"] == "unconfigured"
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json == {"available": False, "user": None}
    assert client.get("/api/history").status_code == 503


def test_signup_login_logout_round_trip(configured_client, service):
    client = configured_client
    response = signup(client)
    assert response.status_code == 201
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Secure" not in cookie
    assert response.json["user"]["email"] == "student@example.com"
    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json["available"] is True
    assert me.json["user"]["email"] == "student@example.com"
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").json["user"] is None
    signed_in = login(client)
    assert signed_in.status_code == 200
    assert signed_in.json["user"]["email"] == "student@example.com"


def test_secure_host_cookie(configured_client):
    response = configured_client.post(
        "/api/auth/signup",
        json={"email": "secure@example.com", "password": PASSWORD},
        headers={"X-Forwarded-Proto": "https", "Host": "app.example.com"},
        environ_base={"REMOTE_ADDR": "203.0.113.11"},
    )
    assert response.status_code == 201
    cookie = response.headers["Set-Cookie"]
    assert cookie.startswith("__Host-p2p_session=")
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_duplicate_email_and_bad_password(configured_client):
    assert signup(configured_client).status_code == 201
    duplicate = signup(configured_client, ip="203.0.113.12")
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json["error"]
    bad = signup(configured_client, email="short@example.com", ip="203.0.113.13")
    assert bad.status_code == 201  # password checked before call only if supplied
    fresh = configured_client.post(
        "/api/auth/signup",
        json={"email": "short@example.com", "password": "short"},
        environ_base={"REMOTE_ADDR": "203.0.113.14"},
    )
    assert fresh.status_code == 422


def test_wrong_password_rates_limited(configured_client):
    assert signup(configured_client).status_code == 201
    configured_client.post("/api/auth/logout")
    for _ in range(8):
        response = login(configured_client, password="wrong password")
        assert response.status_code == 401
    blocked = login(configured_client, password="wrong password")
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "900"


def test_account_history_isolation(configured_client, service):
    from api.index import app

    alice = configured_client
    assert signup(alice, "alice@example.com", "203.0.113.20").status_code == 201
    bob = app.test_client()
    assert signup(bob, "bob@example.com", "203.0.113.21").status_code == 201

    inputs = assessment_inputs()
    inputs["cgpa"] = 9
    inputs["dsa"] = 4
    record_id = str(uuid.uuid4())
    saved = alice.post("/api/history", json={"inputs": inputs, "id": record_id})
    assert saved.status_code == 201
    assert saved.json["record"]["id"] == record_id
    assert alice.get("/api/history").json["assessments"][0]["id"] == record_id
    assert bob.get("/api/history").json["assessments"] == []
    assert bob.delete(f"/api/history/{record_id}").status_code == 404
    assert alice.get("/api/history").json["assessments"][0]["id"] == record_id
    assert alice.delete(f"/api/history/{record_id}").status_code == 204
    assert alice.get("/api/history").json["assessments"] == []


def test_import_recomputes_scores_and_is_idempotent(configured_client):
    assert signup(configured_client).status_code == 201
    weak = {key: spec[1] for key, spec in FIELDS.items()}
    stamp = "2025-01-02T03:04:05Z"
    item = {
        "id": str(uuid.uuid4()),
        "created_at": stamp,
        "inputs": weak,
        "score": 100,
        "band": "Strong Preparation",
    }
    first = configured_client.post("/api/history/import", json={"items": [item]})
    assert first.status_code == 200
    assert first.json["imported"] == 1
    record = first.json["assessments"][0]
    assert record["score"] != 100
    assert record["created_at"].startswith("2025-01-02")
    second = configured_client.post("/api/history/import", json={"items": [item]})
    assert second.status_code == 200
    assert second.json["imported"] == 0
    assert second.json["skipped_existing"] == 1


def test_bad_import_and_body_limits(configured_client):
    assert signup(configured_client).status_code == 201
    bad = configured_client.post("/api/history/import", json={"items": [{"id": "too-short"}]})
    assert bad.status_code == 422
    duplicate = {
        "id": str(uuid.uuid4()),
        "created_at": "2025-01-02T03:04:05Z",
        "inputs": assessment_inputs(),
    }
    response = configured_client.post("/api/history/import", json={"items": [duplicate, duplicate]})
    assert response.status_code == 422
    huge = configured_client.post(
        "/api/history/import",
        data=b"{" + b" " * (550 * 1024) + b"}",
        content_type="application/json",
    )
    assert huge.status_code == 413


def test_corrupt_stored_record_is_not_returned(configured_client, service):
    assert signup(configured_client).status_code == 201
    store = service[1]
    user_id = next(iter(store.profiles))
    store.assessments.append(
        {
            "id": "broken-record",
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "record": {"id": "broken-record", "score": 999},
        }
    )
    result = configured_client.get("/api/history").json
    assert result["assessments"] == []
    assert result["skipped"] == 1


def test_password_change_signs_out_other_sessions(configured_client):
    from api.index import app

    assert signup(configured_client).status_code == 201
    second = app.test_client()
    assert login(second, ip="203.0.113.30").status_code == 200
    assert second.get("/api/auth/me").json["user"] is not None
    changed = configured_client.post(
        "/api/auth/password",
        json={"current_password": PASSWORD, "new_password": "a completely new passphrase"},
    )
    assert changed.status_code == 200
    assert second.get("/api/auth/me").json["user"] is None
    assert configured_client.get("/api/auth/me").json["user"] is not None
    configured_client.post("/api/auth/logout")
    assert login(configured_client, password="a completely new passphrase").status_code == 200


def test_account_data_delete_keeps_auth_login(configured_client, service):
    assert signup(configured_client).status_code == 201
    assert configured_client.post("/api/history", json={"inputs": assessment_inputs()}).status_code == 201
    assert configured_client.delete("/api/account/data").status_code == 204
    assert configured_client.get("/api/auth/me").json["user"] is None
    assert service[2].users["student@example.com"]
    assert service[1].profiles == {}
    assert service[1].assessments == []


def test_csrf_origin_is_rejected(configured_client):
    response = configured_client.post(
        "/api/auth/login",
        json={"email": "student@example.com", "password": PASSWORD},
        headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
    )
    assert response.status_code == 403


def test_unauthenticated_history_and_limit(configured_client, service):
    assert configured_client.get("/api/history").status_code == 401
    assert configured_client.post("/api/history", json={"inputs": assessment_inputs()}).status_code == 401
    assert signup(configured_client).status_code == 201
    user_id = next(iter(service[1].profiles))
    for index in range(200):
        service[1].assessments.append(
            {
                "id": f"assessment-{index:04d}",
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "record": {},
            }
        )
    overflow = configured_client.post("/api/history", json={"inputs": assessment_inputs()})
    assert overflow.status_code == 409


def test_valid_record_matches_server_shape():
    record = _record(assessment_inputs(), str(uuid.uuid4()))
    assert valid_record(record)
    assert not valid_record({**record, "score": 101})
    assert not valid_record({**record, "categories": {}})
    assert not valid_record({**record, "id": "short"})


def test_me_clears_invalid_cookie(configured_client):
    configured_client.set_cookie("p2p_session", "not-a-real-session")
    response = configured_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json["user"] is None
    assert "p2p_session=;" in response.headers.get("Set-Cookie", "")

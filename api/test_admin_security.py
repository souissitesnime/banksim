import json

import pytest
from sqlalchemy import select

from app.models import User
from tests.helpers import PASSWORD, admin_headers, code, make_user, open_account, transfer

pytestmark = pytest.mark.api


# ------------------------------------------------------------------ administration


@pytest.mark.tc("TC-ADM-001")
def test_account_state_machine_freeze_unfreeze(client):
    u = make_user(client)
    acc = open_account(client, u)
    h = admin_headers(client)
    freeze = f"/api/admin/accounts/{acc['id']}/freeze"
    unfreeze = f"/api/admin/accounts/{acc['id']}/unfreeze"
    assert code(client.post(unfreeze, headers=h)) == "INVALID_STATE_TRANSITION"      # ACTIVE -> ACTIVE interdit
    assert client.post(freeze, headers=h).json()["status"] == "FROZEN"               # ACTIVE -> FROZEN
    assert code(client.post(freeze, headers=h)) == "INVALID_STATE_TRANSITION"        # FROZEN -> FROZEN interdit
    assert code(client.post(f"/api/accounts/{acc['id']}/close", headers=u["headers"])) == "ACCOUNT_FROZEN"  # FROZEN -> CLOSED interdit
    assert client.post(unfreeze, headers=h).json()["status"] == "ACTIVE"             # FROZEN -> ACTIVE
    assert client.post(f"/api/accounts/{acc['id']}/close", headers=u["headers"]).json()["status"] == "CLOSED"


@pytest.mark.tc("TC-ADM-001")
def test_freeze_unknown_account_is_404(client):
    r = client.post("/api/admin/accounts/424242/freeze", headers=admin_headers(client))
    assert r.status_code == 404 and code(r) == "ACCOUNT_NOT_FOUND"


@pytest.mark.tc("TC-ADM-002", "TC-SEC-009")
@pytest.mark.parametrize("method,path", [
    ("post", "/api/admin/accounts/1/freeze"), ("post", "/api/admin/accounts/1/unfreeze"),
    ("post", "/api/admin/users/1/unlock"), ("get", "/api/admin/audit-log"),
])
def test_admin_endpoints_require_admin_role(client, method, path):
    u = make_user(client)
    assert getattr(client, method)(path).status_code == 401
    r = getattr(client, method)(path, headers=u["headers"])
    assert r.status_code == 403 and code(r) == "FORBIDDEN"


@pytest.mark.tc("TC-ADM-003")
def test_audit_log_records_key_events_without_secrets(client):
    a, b = make_user(client), make_user(client)
    src, dst = open_account(client, a, balance="50"), open_account(client, b)
    transfer(client, a, src["id"], dst["iban"], "10")
    h = admin_headers(client)
    client.post(f"/api/admin/accounts/{src['id']}/freeze", headers=h)
    for _ in range(3):
        client.post("/api/auth/login", json={"email": b["email"], "password": "Wrong1234"})
    client.post(f"/api/admin/users/{b['id']}/unlock", headers=h)
    log = client.get("/api/admin/audit-log?limit=200", headers=h).json()
    actions = {e["action"] for e in log["items"]}
    assert {"USER_REGISTERED", "ACCOUNT_OPENED", "DEPOSIT", "TRANSFER", "ACCOUNT_FROZEN", "LOGIN_FAILED",
            "USER_LOCKED", "USER_UNLOCKED", "LOGIN_SUCCEEDED"} <= actions
    blob = json.dumps(log).lower()
    assert PASSWORD.lower() not in blob and "wrong1234" not in blob and "pbkdf2" not in blob


@pytest.mark.tc("TC-ADM-003")
@pytest.mark.parametrize("qs,status", [("?limit=1", 200), ("?limit=200", 200), ("?limit=0", 422), ("?limit=201", 422), ("?offset=-1", 422)])
def test_audit_log_pagination_bounds(client, qs, status):
    assert client.get(f"/api/admin/audit-log{qs}", headers=admin_headers(client)).status_code == status


@pytest.mark.tc("TC-ADM-004")
def test_unlock_edge_cases(client):
    u = make_user(client)
    h = admin_headers(client)
    r = client.post(f"/api/admin/users/{u['id']}/unlock", headers=h)
    assert r.status_code == 409 and code(r) == "USER_NOT_LOCKED"
    r = client.post("/api/admin/users/999999/unlock", headers=h)
    assert r.status_code == 404 and code(r) == "USER_NOT_FOUND"


# ------------------------------------------------------------------ sécurité transverse


@pytest.mark.tc("TC-SEC-001")
def test_no_response_ever_contains_password_material(client):
    u = make_user(client)
    acc = open_account(client, u, balance="10")
    bodies = [
        client.get("/api/auth/me", headers=u["headers"]).text,
        client.get("/api/accounts", headers=u["headers"]).text,
        client.get(f"/api/accounts/{acc['id']}", headers=u["headers"]).text,
        client.post("/api/auth/login", json={"email": u["email"], "password": PASSWORD}).text,
    ]
    for body in bodies:
        assert "pbkdf2" not in body.lower() and "password_hash" not in body and PASSWORD not in body


@pytest.mark.tc("TC-SEC-002")
def test_validation_errors_never_echo_the_submitted_password(client):
    secret = "short"
    r = client.post("/api/auth/register", json={"full_name": "A", "email": "a@b.tn", "password": secret})
    assert r.status_code == 422 and secret not in r.text
    r = client.post("/api/auth/login", json={"email": 123, "password": "Sup3rSecret!"})
    assert r.status_code == 422 and "Sup3rSecret!" not in r.text


@pytest.mark.tc("TC-SEC-003")
def test_security_headers(client):
    api = client.get("/api/health")
    assert api.headers["x-content-type-options"] == "nosniff" and api.headers["x-frame-options"] == "DENY"
    assert api.headers["cache-control"] == "no-store" and api.headers["referrer-policy"] == "no-referrer"
    page = client.get("/")
    assert "default-src 'self'" in page.headers["content-security-policy"]


@pytest.mark.tc("TC-SEC-004")
def test_sql_injection_payloads_are_inert(client, app):
    payload = "' OR '1'='1' --"
    assert client.post("/api/auth/login", json={"email": payload, "password": payload}).status_code == 401
    assert client.post("/api/auth/register", json={"full_name": payload, "email": f"x{payload}@a.tn",
                                                    "password": PASSWORD}).status_code == 422
    u = make_user(client, name="Robert'); DROP TABLE users;--")
    acc = open_account(client, u, balance="5")
    r = transfer(client, u, acc["id"], "TN59'; DROP TABLE accounts;--", "1", reference=payload)
    assert code(r) == "INVALID_IBAN"
    other = open_account(client, u)
    assert transfer(client, u, acc["id"], other["iban"], "1", reference="'; DROP TABLE transactions;--").status_code == 201
    assert client.get("/api/accounts", headers=u["headers"]).status_code == 200
    with app.state.SessionLocal() as db:
        assert db.scalars(select(User).where(User.id == u["id"])).one().full_name.startswith("Robert")


@pytest.mark.tc("TC-SEC-005")
def test_production_refuses_default_secrets(monkeypatch, make_app):
    monkeypatch.setenv("BANKSIM_ENV", "production")
    with pytest.raises(RuntimeError):
        make_app()
    monkeypatch.setenv("BANKSIM_SECRET", "a-long-random-production-secret-0123456789")
    with pytest.raises(RuntimeError):                    # le mot de passe admin par défaut est encore refusé
        make_app()
    monkeypatch.setenv("BANKSIM_ADMIN_PASSWORD", "Another-Strong-Pass-123")
    assert make_app() is not None


@pytest.mark.tc("TC-SEC-007")
def test_unknown_routes_and_methods_use_the_error_envelope(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and code(r) == "NOT_FOUND"
    r = client.delete("/api/accounts")
    assert r.status_code == 405 and code(r) == "METHOD_NOT_ALLOWED"


@pytest.mark.tc("TC-SEC-010")
def test_bootstrap_is_idempotent_and_admin_exists_once(tmp_path, make_app):
    url = f"sqlite:///{tmp_path / 'boot.db'}"
    make_app(url)
    app2 = make_app(url)                              # redémarrage sur la même base
    with app2.state.SessionLocal() as db:
        assert len(db.scalars(select(User).where(User.role == "ADMIN")).all()) == 1


@pytest.mark.tc("TC-UI-000")
def test_ui_assets_are_served(client):
    page = client.get("/")
    assert page.status_code == 200 and "BankSim" in page.text
    assert client.get("/static/app.js").status_code == 200 and client.get("/static/style.css").status_code == 200
    assert "innerHTML" not in client.get("/static/app.js").text       # garde-fou anti-XSS dans l'interface
    assert client.get("/docs").status_code == 200                    # Swagger UI pour la démo


@pytest.mark.tc("TC-SEC-011")
def test_cors_is_not_enabled(client):
    r = client.options("/api/accounts", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


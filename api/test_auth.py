import base64
import json
import time

import jwt
import pytest
from sqlalchemy import select

from app import security
from app.models import User
from tests.helpers import PASSWORD, admin_headers, code, make_user, new_email

pytestmark = pytest.mark.api


def _register(client, **over):
    body = {"full_name": "Amira Ben Salah", "email": new_email(), "password": PASSWORD, **over}
    return client.post("/api/auth/register", json=body)


# ------------------------------------------------------------------ inscription


@pytest.mark.tc("TC-AUTH-001")
def test_register_ok_normalizes_fields(client):
    r = _register(client, full_name="  Amira Ben Salah ", email="Amira@Example.TN")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "amira@example.tn" and body["full_name"] == "Amira Ben Salah"
    assert body["role"] == "CUSTOMER"
    assert "password" not in json.dumps(body).lower()


@pytest.mark.tc("TC-AUTH-002")
@pytest.mark.parametrize("email", ["plainaddress", "@no-user.tn", "user@", "user@domain", "user@domain.c",
                                   "user name@x.tn", ""])
def test_register_invalid_email_partitions(client, email):
    r = _register(client, email=email)
    assert r.status_code == 422 and code(r) == "VALIDATION_ERROR"


@pytest.mark.tc("TC-AUTH-003")
@pytest.mark.parametrize("length,ok", [(7, False), (8, True), (9, True), (63, True), (64, True), (65, False)])
def test_register_password_length_boundaries(client, length, ok):
    pwd = "Aa1" + "x" * (length - 3)
    assert len(pwd) == length
    assert (_register(client, password=pwd).status_code == 201) is ok


@pytest.mark.tc("TC-AUTH-004")
@pytest.mark.parametrize("pwd", ["abcdefg1", "ABCDEFG1", "Abcdefgh", "12345678"])
def test_register_password_missing_character_class(client, pwd):
    r = _register(client, password=pwd)
    assert r.status_code == 422 and code(r) == "VALIDATION_ERROR"


@pytest.mark.tc("TC-AUTH-008")
def test_register_password_digit_must_be_ascii(client):
    """DEF-003 (corrigé) : un chiffre arabe-indien ne compte pas comme « chiffre » de la politique de mot de passe."""
    assert _register(client, password="Abcdefgh٥").status_code == 422
    assert _register(client, password="Abcdefgh5").status_code == 201


@pytest.mark.tc("TC-AUTH-005")
def test_register_duplicate_email_is_case_insensitive(client):
    assert _register(client, email="dup@example.tn").status_code == 201
    r = _register(client, email="DUP@Example.TN")
    assert r.status_code == 409 and code(r) == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.tc("TC-AUTH-006")
@pytest.mark.parametrize("name,ok", [("", False), ("   ", False), ("A", True), ("N" * 100, True), ("N" * 101, False)])
def test_register_name_boundaries(client, name, ok):
    assert (_register(client, full_name=name).status_code == 201) is ok


@pytest.mark.tc("TC-AUTH-007", "TC-SEC-008")
def test_register_rejects_mass_assignment(client):
    r = _register(client, role="ADMIN")
    assert r.status_code == 422
    assert any(d["field"] == "role" for d in r.json()["error"]["details"])


# ------------------------------------------------------------------ connexion


@pytest.mark.tc("TC-AUTH-010")
def test_login_ok_and_me(client):
    u = make_user(client, email="Login@Example.TN")
    r = client.post("/api/auth/login", json={"email": "LOGIN@example.tn", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["id"] == u["id"] and me.json()["email"] == "login@example.tn"


@pytest.mark.tc("TC-AUTH-011")
def test_login_wrong_password_and_unknown_email_look_identical(client):
    u = make_user(client)
    wrong = client.post("/api/auth/login", json={"email": u["email"], "password": "Wrong1234"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.tn", "password": "Wrong1234"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() and code(wrong) == "INVALID_CREDENTIALS"


@pytest.mark.tc("TC-AUTH-012")
def test_failed_attempts_counter_is_reset_by_success(client):
    u = make_user(client)
    bad = {"email": u["email"], "password": "Wrong1234"}
    good = {"email": u["email"], "password": PASSWORD}
    assert client.post("/api/auth/login", json=bad).status_code == 401      # 1
    assert client.post("/api/auth/login", json=bad).status_code == 401      # 2
    assert client.post("/api/auth/login", json=good).status_code == 200     # succès -> compteur à 0
    assert client.post("/api/auth/login", json=bad).status_code == 401      # 1
    assert client.post("/api/auth/login", json=bad).status_code == 401      # 2 (pas de verrouillage)
    assert client.post("/api/auth/login", json=good).status_code == 200


@pytest.mark.tc("TC-AUTH-013")
def test_third_consecutive_failure_locks_even_for_correct_password(client):
    u = make_user(client)
    bad = {"email": u["email"], "password": "Wrong1234"}
    assert client.post("/api/auth/login", json=bad).status_code == 401
    assert client.post("/api/auth/login", json=bad).status_code == 401
    third = client.post("/api/auth/login", json=bad)
    assert third.status_code == 423 and code(third) == "ACCOUNT_LOCKED"
    right = client.post("/api/auth/login", json={"email": u["email"], "password": PASSWORD})
    assert right.status_code == 423 and code(right) == "ACCOUNT_LOCKED"


@pytest.mark.tc("TC-AUTH-014")
def test_admin_unlock_restores_access(client):
    u = make_user(client)
    for _ in range(3):
        client.post("/api/auth/login", json={"email": u["email"], "password": "Wrong1234"})
    r = client.post(f"/api/admin/users/{u['id']}/unlock", headers=admin_headers(client))
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"email": u["email"], "password": PASSWORD}).status_code == 200


# ------------------------------------------------------------------ jetons


def _b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


@pytest.mark.tc("TC-AUTH-020")
def test_expired_token_gets_401_token_expired(client):
    u = make_user(client)
    token = security.create_token(u["id"], "CUSTOMER", ttl_minutes=-1)
    r = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401 and code(r) == "TOKEN_EXPIRED"


@pytest.mark.tc("TC-AUTH-021")
def test_tampered_or_foreign_signature_is_rejected(client):
    u = make_user(client)
    token = u["headers"]["Authorization"].split()[1]
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    foreign = jwt.encode({"sub": str(u["id"]), "exp": time.time() + 600}, "another-secret-another-secret-0123456789",
                         algorithm="HS256")
    for bad in (tampered, foreign, "not-a-jwt"):
        r = client.get("/api/accounts", headers={"Authorization": f"Bearer {bad}"})
        assert r.status_code == 401 and code(r) == "INVALID_TOKEN"


@pytest.mark.tc("TC-AUTH-022")
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer"}])
def test_missing_or_malformed_authorization(client, headers):
    r = client.get("/api/accounts", headers=headers)
    assert r.status_code == 401 and code(r) == "UNAUTHENTICATED"


@pytest.mark.tc("TC-AUTH-023")
def test_alg_none_token_is_rejected(client):
    unsigned = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64({'sub': '1', 'role': 'ADMIN', 'exp': 4102444800})}."
    r = client.get("/api/admin/audit-log", headers={"Authorization": f"Bearer {unsigned}"})
    assert r.status_code == 401 and code(r) == "INVALID_TOKEN"


@pytest.mark.tc("TC-AUTH-021")
def test_token_with_non_numeric_or_unknown_subject_is_rejected(client):
    from app.config import get_settings
    for sub in ("abc", "999999"):
        tok = jwt.encode({"sub": sub, "exp": time.time() + 600}, get_settings().secret, algorithm="HS256")
        r = client.get("/api/accounts", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 401 and code(r) == "INVALID_TOKEN"


@pytest.mark.tc("TC-AUTH-024")
def test_token_of_locked_user_is_refused(client):
    u = make_user(client)
    for _ in range(3):
        client.post("/api/auth/login", json={"email": u["email"], "password": "Wrong1234"})
    r = client.get("/api/accounts", headers=u["headers"])  # le jeton émis avant le verrouillage
    assert r.status_code == 423 and code(r) == "ACCOUNT_LOCKED"


@pytest.mark.tc("TC-AUTH-025")
def test_token_role_claim_is_not_trusted(client):
    """Un client ne peut pas s'octroyer le rôle ADMIN en forgeant la revendication « role » (signée avec le vrai secret
    par un client qui l'aurait obtenu) : le rôle est relu en base."""
    from app.config import get_settings
    u = make_user(client)
    tok = jwt.encode({"sub": str(u["id"]), "role": "ADMIN", "exp": time.time() + 600}, get_settings().secret,
                     algorithm="HS256")
    r = client.get("/api/admin/audit-log", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403 and code(r) == "FORBIDDEN"


@pytest.mark.tc("TC-SEC-001")
def test_password_hashes_differ_for_same_password(client, app):
    make_user(client, email="same1@example.tn")
    make_user(client, email="same2@example.tn")
    with app.state.SessionLocal() as db:
        hashes = [u.password_hash for u in db.scalars(select(User).where(User.email.like("same%")))]
    assert len(hashes) == 2 and hashes[0] != hashes[1]
    assert all(PASSWORD not in h for h in hashes)

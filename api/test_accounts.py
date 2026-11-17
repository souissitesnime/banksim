import re

import pytest

from app import money
from tests.helpers import admin_headers, balance, code, deposit, make_user, open_account

pytestmark = pytest.mark.api


@pytest.mark.tc("TC-ACC-001", "TC-ACC-002")
@pytest.mark.parametrize("kind", ["CHECKING", "SAVINGS"])
def test_open_account(client, kind):
    u = make_user(client)
    r = client.post("/api/accounts", json={"type": kind}, headers=u["headers"])
    assert r.status_code == 201
    acc = r.json()
    assert acc["type"] == kind and acc["status"] == "ACTIVE" and acc["balance"] == "0.000" and acc["currency"] == "TND"
    assert re.fullmatch(r"TN\d{22}", acc["iban"]) and money.is_valid_iban(acc["iban"])


@pytest.mark.tc("TC-ACC-003")
@pytest.mark.parametrize("body", [{"type": "BUSINESS"}, {"type": ""}, {}, {"type": "CHECKING", "balance": "999"},
                                  {"type": "checking"}])
def test_open_account_invalid_payload(client, body):
    u = make_user(client)
    r = client.post("/api/accounts", json=body, headers=u["headers"])
    assert r.status_code == 422 and code(r) == "VALIDATION_ERROR"


@pytest.mark.tc("TC-ACC-004")
def test_sixth_open_account_is_refused(client):
    u = make_user(client)
    for _ in range(5):
        assert client.post("/api/accounts", json={"type": "CHECKING"}, headers=u["headers"]).status_code == 201
    r = client.post("/api/accounts", json={"type": "SAVINGS"}, headers=u["headers"])
    assert r.status_code == 409 and code(r) == "ACCOUNT_LIMIT_REACHED"


@pytest.mark.tc("TC-ACC-005")
def test_closed_accounts_do_not_count_toward_the_limit(client):
    u = make_user(client)
    accounts = [open_account(client, u) for _ in range(5)]
    assert client.post(f"/api/accounts/{accounts[0]['id']}/close", headers=u["headers"]).status_code == 200
    assert client.post("/api/accounts", json={"type": "CHECKING"}, headers=u["headers"]).status_code == 201


@pytest.mark.tc("TC-ACC-006")
def test_list_returns_only_own_accounts_newest_first(client):
    a, b = make_user(client), make_user(client)
    a1, a2 = open_account(client, a), open_account(client, a, "SAVINGS")
    open_account(client, b)
    r = client.get("/api/accounts", headers=a["headers"])
    assert [x["id"] for x in r.json()] == [a2["id"], a1["id"]]


@pytest.mark.tc("TC-ACC-007", "TC-SEC-009")
def test_other_customers_account_is_invisible_idor(client):
    a, b = make_user(client), make_user(client)
    acc = open_account(client, a, balance="100")
    r = client.get(f"/api/accounts/{acc['id']}", headers=b["headers"])
    assert r.status_code == 404 and code(r) == "ACCOUNT_NOT_FOUND"
    # même réponse qu'un compte qui n'existe pas : on ne révèle pas l'existence
    assert client.get("/api/accounts/987654", headers=b["headers"]).json() == r.json()
    assert client.post(f"/api/accounts/{acc['id']}/close", headers=b["headers"]).status_code == 404
    assert client.get(f"/api/accounts/{acc['id']}/interest-projection", headers=b["headers"]).status_code == 404


@pytest.mark.tc("TC-ACC-007")
def test_admin_can_read_any_account(client):
    a = make_user(client)
    acc = open_account(client, a, balance="12.5")
    r = client.get(f"/api/accounts/{acc['id']}", headers=admin_headers(client))
    assert r.status_code == 200 and r.json()["balance"] == "12.500"


@pytest.mark.tc("TC-ACC-008")
def test_close_requires_zero_balance(client):
    u = make_user(client)
    acc = open_account(client, u, balance="0.001")
    r = client.post(f"/api/accounts/{acc['id']}/close", headers=u["headers"])
    assert r.status_code == 409 and code(r) == "BALANCE_NOT_ZERO"
    assert client.post(f"/api/accounts/{acc['id']}/withdraw", json={"amount": "0.001"}, headers=u["headers"]).status_code == 201
    r = client.post(f"/api/accounts/{acc['id']}/close", headers=u["headers"])
    assert r.status_code == 200 and r.json()["status"] == "CLOSED"


@pytest.mark.tc("TC-ACC-009")
def test_closed_account_is_terminal(client):
    u = make_user(client)
    acc = open_account(client, u)
    client.post(f"/api/accounts/{acc['id']}/close", headers=u["headers"])
    assert code(client.post(f"/api/accounts/{acc['id']}/close", headers=u["headers"])) == "ACCOUNT_CLOSED"
    assert code(deposit(client, u, acc["id"], "1")) == "ACCOUNT_CLOSED"
    assert code(client.post(f"/api/accounts/{acc['id']}/withdraw", json={"amount": "1"}, headers=u["headers"])) == "ACCOUNT_CLOSED"
    # un compte clôturé reste visible dans la liste (historique)
    listed = client.get("/api/accounts", headers=u["headers"]).json()
    assert listed[0]["status"] == "CLOSED"
    # et un administrateur ne peut ni le geler ni le dégeler
    h = admin_headers(client)
    assert code(client.post(f"/api/admin/accounts/{acc['id']}/freeze", headers=h)) == "INVALID_STATE_TRANSITION"
    assert code(client.post(f"/api/admin/accounts/{acc['id']}/unfreeze", headers=h)) == "INVALID_STATE_TRANSITION"


@pytest.mark.tc("TC-ACC-010")
def test_ibans_are_unique_across_many_accounts(client):
    ibans = set()
    for _ in range(4):
        u = make_user(client)
        for _ in range(5):
            ibans.add(open_account(client, u)["iban"])
    assert len(ibans) == 20


@pytest.mark.tc("TC-ACC-011")
def test_non_integer_account_id_is_a_validation_error(client):
    u = make_user(client)
    r = client.get("/api/accounts/abc", headers=u["headers"])
    assert r.status_code == 422 and code(r) == "VALIDATION_ERROR"
    assert balance(client, u, open_account(client, u)["id"]) == 0

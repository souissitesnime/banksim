from datetime import datetime
from decimal import Decimal

import pytest

from tests.helpers import admin_headers, balance, code, deposit, make_user, open_account, withdraw

pytestmark = pytest.mark.api


# ------------------------------------------------------------------ dépôt


@pytest.mark.tc("TC-DEP-001")
@pytest.mark.parametrize("amount,status,err", [
    ("-0.001", 422, "AMOUNT_OUT_OF_RANGE"), ("0", 422, "AMOUNT_OUT_OF_RANGE"), ("0.000", 422, "AMOUNT_OUT_OF_RANGE"),
    ("0.001", 201, None), ("0.002", 201, None), ("25000", 201, None),
    ("49999.999", 201, None), ("50000.000", 201, None), ("50000.001", 422, "AMOUNT_OUT_OF_RANGE"),
])
def test_deposit_amount_boundaries(client, amount, status, err):
    u = make_user(client)
    acc = open_account(client, u)
    r = deposit(client, u, acc["id"], amount)
    assert r.status_code == status
    if err:
        assert code(r) == err and balance(client, u, acc["id"]) == 0
    else:
        assert balance(client, u, acc["id"]) == Decimal(amount)


@pytest.mark.tc("TC-DEP-002")
@pytest.mark.parametrize("amount", ["1.0001", "abc", "", "NaN", "Infinity", "-Infinity", None, [], {}, "1e30", "1,5"])
def test_deposit_invalid_amount_formats(client, amount):
    u = make_user(client)
    acc = open_account(client, u)
    r = deposit(client, u, acc["id"], amount)
    assert r.status_code == 422 and code(r) == "VALIDATION_ERROR"
    assert balance(client, u, acc["id"]) == 0


@pytest.mark.tc("TC-DEP-002")
def test_deposit_requires_amount_and_rejects_extra_fields(client):
    u = make_user(client)
    acc = open_account(client, u)
    url = f"/api/accounts/{acc['id']}/deposit"
    assert client.post(url, json={}, headers=u["headers"]).status_code == 422
    assert client.post(url, json={"amount": "1", "balance": "999999"}, headers=u["headers"]).status_code == 422
    assert client.post(url, content="not json", headers={**u["headers"], "Content-Type": "application/json"}).status_code == 422


@pytest.mark.tc("TC-DEP-005")
def test_deposit_number_and_string_are_equivalent_without_float_drift(client):
    u = make_user(client)
    acc = open_account(client, u)
    assert deposit(client, u, acc["id"], 10.5).status_code == 201
    assert deposit(client, u, acc["id"], "10.500").status_code == 201
    assert deposit(client, u, acc["id"], 0.1).status_code == 201
    assert deposit(client, u, acc["id"], 0.2).status_code == 201
    assert balance(client, u, acc["id"]) == Decimal("21.300")  # exactement 21,300 (pas 21.299999…)


@pytest.mark.tc("TC-DEP-007")
@pytest.mark.parametrize("amount", [
    "1_000", "1e2", " 5 ", "+5", "5.", ".5", "00005", "٥", "５", "٠.٥٠٠", "0.0010", "10.5000", "1 000", "0x10", "--5",
])
def test_amount_must_be_canonical_decimal_string(client, amount):
    """DEF-001 (corrigé) : l'API refuse tout format non canonique, même si Decimal() le comprendrait."""
    u = make_user(client)
    acc = open_account(client, u)
    r = deposit(client, u, acc["id"], amount)
    assert r.status_code == 422 and code(r) == "VALIDATION_ERROR"
    assert balance(client, u, acc["id"]) == 0


@pytest.mark.tc("TC-DEP-007")
@pytest.mark.parametrize("amount,expected", [("0", "0.000"), ("0.5", "0.500"), ("10", "10.000"), ("10.5", "10.500"),
                                             ("1234.567", "1234.567"), (7, "7.000"), (0.25, "0.250")])
def test_canonical_amounts_are_accepted_as_string_or_number(client, amount, expected):
    u = make_user(client)
    acc = open_account(client, u, balance="5000")
    r = withdraw(client, u, acc["id"], amount)           # 0 -> 422 (plage) ; les autres sont dans la plage
    if expected == "0.000":
        assert code(r) == "AMOUNT_OUT_OF_RANGE"
    else:
        assert r.status_code == 201 and r.json()["amount"] == "-" + expected


@pytest.mark.tc("TC-DEP-003")
def test_deposit_on_frozen_account_is_allowed(client):
    u = make_user(client)
    acc = open_account(client, u)
    client.post(f"/api/admin/accounts/{acc['id']}/freeze", headers=admin_headers(client))
    assert deposit(client, u, acc["id"], "5").status_code == 201
    assert balance(client, u, acc["id"]) == Decimal("5")


@pytest.mark.tc("TC-DEP-004")
def test_deposit_on_someone_elses_account_is_404(client):
    a, b = make_user(client), make_user(client)
    acc = open_account(client, a)
    r = deposit(client, b, acc["id"], "5")
    assert r.status_code == 404 and code(r) == "ACCOUNT_NOT_FOUND"
    assert balance(client, a, acc["id"]) == 0


@pytest.mark.tc("TC-DEP-006")
def test_operations_require_authentication(client):
    u = make_user(client)
    acc = open_account(client, u)
    for path in ("deposit", "withdraw"):
        r = client.post(f"/api/accounts/{acc['id']}/{path}", json={"amount": "1"})
        assert r.status_code == 401 and code(r) == "UNAUTHENTICATED"


# ------------------------------------------------------------------ retrait


@pytest.mark.tc("TC-WDR-001")
@pytest.mark.parametrize("amount,status", [
    ("0", 422), ("-1", 422), ("0.001", 201), ("1999.999", 201), ("2000.000", 201), ("2000.001", 422),
])
def test_withdraw_amount_boundaries(client, amount, status):
    u = make_user(client)
    acc = open_account(client, u, balance="5000")
    r = withdraw(client, u, acc["id"], amount)
    assert r.status_code == status
    expected = Decimal("5000") - (Decimal(amount) if status == 201 else 0)
    assert balance(client, u, acc["id"]) == expected
    if status == 422:
        assert code(r) == "AMOUNT_OUT_OF_RANGE"


@pytest.mark.tc("TC-WDR-002")
@pytest.mark.parametrize("kind,start,amount,ok", [
    ("CHECKING", "100", "600", True),         # solde final = -500,000 : exactement le découvert autorisé
    ("CHECKING", "100", "600.001", False),    # -500,001 : un millime de trop
    ("CHECKING", "0", "500", True),
    ("SAVINGS", "100", "100", True),          # solde final 0,000
    ("SAVINGS", "100", "100.001", False),     # l'épargne ne peut pas être débitrice
])
def test_withdraw_overdraft_floor(client, kind, start, amount, ok):
    u = make_user(client)
    acc = open_account(client, u, kind, balance=start)
    r = withdraw(client, u, acc["id"], amount)
    assert (r.status_code == 201) is ok
    if not ok:
        assert code(r) == "INSUFFICIENT_FUNDS" and balance(client, u, acc["id"]) == Decimal(start)
    else:
        assert balance(client, u, acc["id"]) == Decimal(start) - Decimal(amount)


@pytest.mark.tc("TC-WDR-003")
def test_daily_limit_exact_boundary(client, fake_clock):
    u = make_user(client)
    acc = open_account(client, u, balance="10000")
    for amount in ("2000", "2000", "1000"):
        assert withdraw(client, u, acc["id"], amount).status_code == 201     # total = 5000,000 : accepté
    r = withdraw(client, u, acc["id"], "0.001")
    assert r.status_code == 422 and code(r) == "DAILY_LIMIT_EXCEEDED"       # 5000,001 : refusé
    assert balance(client, u, acc["id"]) == Decimal("5000")


@pytest.mark.tc("TC-WDR-003")
def test_daily_limit_resets_at_midnight_utc(client, fake_clock):
    u = make_user(client)
    acc = open_account(client, u, balance="10000")
    fake_clock.set(datetime(2026, 11, 16, 23, 59, 59, 999999))
    for amount in ("2000", "2000", "1000"):
        assert withdraw(client, u, acc["id"], amount).status_code == 201
    assert code(withdraw(client, u, acc["id"], "1")) == "DAILY_LIMIT_EXCEEDED"
    fake_clock.set(datetime(2026, 11, 17, 0, 0, 0))                            # nouveau jour : compteur remis à zéro
    assert withdraw(client, u, acc["id"], "2000").status_code == 201


@pytest.mark.tc("TC-WDR-004")
def test_withdraw_on_frozen_or_closed_account(client):
    u = make_user(client)
    frozen = open_account(client, u, balance="100")
    closed = open_account(client, u)
    client.post(f"/api/admin/accounts/{frozen['id']}/freeze", headers=admin_headers(client))
    client.post(f"/api/accounts/{closed['id']}/close", headers=u["headers"])
    assert code(withdraw(client, u, frozen["id"], "1")) == "ACCOUNT_FROZEN"
    assert code(withdraw(client, u, closed["id"], "1")) == "ACCOUNT_CLOSED"
    assert balance(client, u, frozen["id"]) == Decimal("100")


def _prepare(client, state, prior_out):
    u = make_user(client)
    acc = open_account(client, u, balance="10000" if prior_out else "1000")
    for amount in prior_out:
        assert withdraw(client, u, acc["id"], amount).status_code == 201
    if state == "FROZEN":
        client.post(f"/api/admin/accounts/{acc['id']}/freeze", headers=admin_headers(client))
    if state == "CLOSED":
        acc = open_account(client, u)
        client.post(f"/api/accounts/{acc['id']}/close", headers=u["headers"])
    return u, acc


@pytest.mark.tc("TC-WDR-005")
@pytest.mark.parametrize("state,prior_out,amount,expected", [
    ("ACTIVE", [], "100", "OK"),
    ("ACTIVE", [], "2000.001", "AMOUNT_OUT_OF_RANGE"),
    ("ACTIVE", [], "1501", "INSUFFICIENT_FUNDS"),
    ("ACTIVE", ["2000", "1500"], "2000", "DAILY_LIMIT_EXCEEDED"),
    ("FROZEN", [], "100", "ACCOUNT_FROZEN"),
    ("CLOSED", [], "100", "ACCOUNT_CLOSED"),
    ("ACTIVE", [], "2500", "AMOUNT_OUT_OF_RANGE"),        # plage ET fonds insuffisants -> la plage est contrôlée d'abord
    ("FROZEN", [], "2500", "ACCOUNT_FROZEN"),             # état ET plage -> l'état est contrôlé d'abord
])
def test_withdraw_decision_table_and_precedence(client, fake_clock, state, prior_out, amount, expected):
    u, acc = _prepare(client, state, prior_out)
    r = withdraw(client, u, acc["id"], amount)
    if expected == "OK":
        assert r.status_code == 201
    else:
        assert code(r) == expected


@pytest.mark.tc("TC-WDR-006")
def test_check_precedence_auth_then_format_then_ownership_then_state_then_range(client):
    a, b = make_user(client), make_user(client)
    acc = open_account(client, a)
    url = f"/api/accounts/{acc['id']}/deposit"
    assert client.post(url, json={"amount": "abc"}).status_code == 401                 # authentification d'abord
    assert code(deposit(client, b, acc["id"], "abc")) == "VALIDATION_ERROR"             # format avant propriété
    assert code(deposit(client, b, acc["id"], "99999")) == "ACCOUNT_NOT_FOUND"          # propriété avant plage
    client.post(f"/api/accounts/{acc['id']}/close", headers=a["headers"])
    assert code(deposit(client, a, acc["id"], "99999")) == "ACCOUNT_CLOSED"             # état avant plage

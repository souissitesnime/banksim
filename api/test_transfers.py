from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app import money, services
from app.models import Account, IdempotencyRecord, Transaction
from tests.helpers import admin_headers, balance, code, deposit, make_user, open_account, transfer, withdraw

pytestmark = pytest.mark.api


@pytest.fixture
def world(client):
    """Alice : courant C1 (5000), courant C2, épargne S1 (5000). Bob : courant B1."""
    alice, bob = make_user(client), make_user(client)
    return {
        "alice": alice, "bob": bob,
        "c1": open_account(client, alice, "CHECKING", "5000"),
        "c2": open_account(client, alice, "CHECKING"),
        "s1": open_account(client, alice, "SAVINGS", "5000"),
        "b1": open_account(client, bob, "CHECKING"),
    }


@pytest.mark.tc("TC-TRF-001")
def test_transfer_between_own_accounts_is_free(client, world):
    w = world
    r = transfer(client, w["alice"], w["c1"]["id"], w["c2"]["iban"], "250.250", reference="Mise de côté")
    assert r.status_code == 201
    body = r.json()
    assert body["fee"] == "0.000" and body["amount"] == "250.250" and body["from_balance_after"] == "4749.750"
    assert balance(client, w["alice"], w["c1"]["id"]) == Decimal("4749.750")
    assert balance(client, w["alice"], w["c2"]["id"]) == Decimal("250.250")
    out = client.get(f"/api/accounts/{w['c1']['id']}/transactions?type=TRANSFER_OUT", headers=w["alice"]["headers"]).json()
    assert out["total"] == 1 and out["items"][0]["amount"] == "-250.250"
    assert out["items"][0]["counterparty_iban"] == w["c2"]["iban"] and out["items"][0]["reference"] == "Mise de côté"


@pytest.mark.tc("TC-TRF-002", "TC-TRF-019")
def test_transfer_to_another_customer_charges_fee_booked_to_revenue(client, app, world):
    w = world
    r = transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "100")
    assert r.status_code == 201 and r.json()["fee"] == "0.500"
    assert balance(client, w["alice"], w["c1"]["id"]) == Decimal("4899.500")
    assert balance(client, w["bob"], w["b1"]["id"]) == Decimal("100")
    with app.state.SessionLocal() as db:
        revenue = db.scalars(select(Account).where(Account.type == "REVENUE")).one()
        assert revenue.balance == 500


@pytest.mark.tc("TC-TRF-003")
@pytest.mark.parametrize("amount,fee", [("0.001", "0.500"), ("999.999", "0.500"), ("1000.000", "0.500"),
                                        ("1000.001", "2.000"), ("3000.000", "2.000")])
def test_fee_boundaries_through_the_api(client, world, amount, fee):
    r = transfer(client, world["alice"], world["c1"]["id"], world["b1"]["iban"], amount)
    assert r.status_code == 201 and r.json()["fee"] == fee


@pytest.mark.tc("TC-TRF-004")
@pytest.mark.parametrize("amount,ok", [("0", False), ("-5", False), ("0.001", True), ("3000.000", True), ("3000.001", False)])
def test_transfer_amount_boundaries(client, world, amount, ok):
    r = transfer(client, world["alice"], world["c1"]["id"], world["c2"]["iban"], amount)
    assert (r.status_code == 201) is ok
    if not ok:
        assert code(r) == "AMOUNT_OUT_OF_RANGE"


@pytest.mark.tc("TC-TRF-005")
def test_funds_check_includes_the_fee(client):
    a, b = make_user(client), make_user(client)
    src, dst = open_account(client, a), open_account(client, b)         # solde 0, découvert -500
    r = transfer(client, a, src["id"], dst["iban"], "499.501")          # + frais 0,500 = 500,001 : un millime de trop
    assert r.status_code == 422 and code(r) == "INSUFFICIENT_FUNDS"
    r = transfer(client, a, src["id"], dst["iban"], "499.500")          # + frais 0,500 = 500,000 : exactement le plancher
    assert r.status_code == 201
    assert balance(client, a, src["id"]) == Decimal("-500.000")


@pytest.mark.tc("TC-TRF-006")
@pytest.mark.parametrize("source,dest,expected", [
    ("c1", "c2", "OK"), ("s1", "c2", "OK"), ("s1", "b1", "SAVINGS_TRANSFER_RESTRICTED"), ("c1", "s1", "OK"),
])
def test_savings_transfer_restriction_decision_table(client, world, source, dest, expected):
    r = transfer(client, world["alice"], world[source]["id"], world[dest]["iban"], "10")
    if expected == "OK":
        assert r.status_code == 201
    else:
        assert r.status_code == 422 and code(r) == expected


@pytest.mark.tc("TC-TRF-007")
@pytest.mark.parametrize("iban", ["TN59", "FR7630006000011234567890189", "TN" + "0" * 22, "tn!@#", "x" * 40])
def test_invalid_iban_is_rejected(client, world, iban):
    r = transfer(client, world["alice"], world["c1"]["id"], iban, "1")
    assert r.status_code == 422 and code(r) == "INVALID_IBAN"


@pytest.mark.tc("TC-TRF-007")
def test_iban_with_spaces_and_lowercase_is_accepted(client, world):
    spaced = " ".join(world["b1"]["iban"][i:i + 4] for i in range(0, 24, 4)).lower()
    assert transfer(client, world["alice"], world["c1"]["id"], spaced, "1").status_code == 201


@pytest.mark.tc("TC-TRF-008")
def test_unknown_but_well_formed_iban_is_404(client, world):
    ghost = money.build_iban("0000000000042")
    r = transfer(client, world["alice"], world["c1"]["id"], ghost, "1")
    assert r.status_code == 404 and code(r) == "DESTINATION_NOT_FOUND"


@pytest.mark.tc("TC-TRF-009")
def test_transfer_to_same_account_is_refused(client, world):
    r = transfer(client, world["alice"], world["c1"]["id"], world["c1"]["iban"], "1")
    assert r.status_code == 422 and code(r) == "SAME_ACCOUNT"


@pytest.mark.tc("TC-TRF-010")
def test_destination_closed_refused_destination_frozen_accepted(client, world):
    w = world
    closed = open_account(client, w["bob"])
    client.post(f"/api/accounts/{closed['id']}/close", headers=w["bob"]["headers"])
    r = transfer(client, w["alice"], w["c1"]["id"], closed["iban"], "1")
    assert r.status_code == 409 and code(r) == "DESTINATION_CLOSED"
    client.post(f"/api/admin/accounts/{w['b1']['id']}/freeze", headers=admin_headers(client))
    assert transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "10").status_code == 201


@pytest.mark.tc("TC-TRF-011")
def test_transfer_from_frozen_or_closed_source_is_refused(client, world):
    w = world
    client.post(f"/api/admin/accounts/{w['c1']['id']}/freeze", headers=admin_headers(client))
    assert code(transfer(client, w["alice"], w["c1"]["id"], w["c2"]["iban"], "1")) == "ACCOUNT_FROZEN"
    closed = open_account(client, w["alice"])
    client.post(f"/api/accounts/{closed['id']}/close", headers=w["alice"]["headers"])
    assert code(transfer(client, w["alice"], closed["id"], w["c2"]["iban"], "1")) == "ACCOUNT_CLOSED"


@pytest.mark.tc("TC-TRF-012")
def test_idempotent_replay_executes_only_once(client, world):
    w = world
    first = transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "100", key="pay-001")
    again = transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "100", key="pay-001")
    assert first.status_code == again.status_code == 201
    assert first.json() == again.json()
    assert "idempotent-replay" not in first.headers and again.headers["idempotent-replay"] == "true"
    assert balance(client, w["alice"], w["c1"]["id"]) == Decimal("4899.500")   # débité une seule fois
    assert balance(client, w["bob"], w["b1"]["id"]) == Decimal("100")
    out = client.get(f"/api/accounts/{w['c1']['id']}/transactions?type=TRANSFER_OUT", headers=w["alice"]["headers"])
    assert out.json()["total"] == 1


@pytest.mark.tc("TC-TRF-013")
def test_idempotency_key_reuse_with_other_payload_is_a_conflict(client, world):
    w = world
    assert transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "100", key="k-1").status_code == 201
    r = transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "101", key="k-1")
    assert r.status_code == 409 and code(r) == "IDEMPOTENCY_KEY_REUSED"
    assert balance(client, w["bob"], w["b1"]["id"]) == Decimal("100")


@pytest.mark.tc("TC-TRF-013")
def test_idempotency_keys_are_scoped_per_user_and_length_checked(client, world):
    w = world
    carol = make_user(client)
    c_acc = open_account(client, carol, balance="50")
    assert transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "5", key="shared").status_code == 201
    assert transfer(client, carol, c_acc["id"], w["b1"]["iban"], "5", key="shared").status_code == 201
    assert transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "5", key="x" * 128).status_code == 201
    assert code(transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "5", key="x" * 129)) == "VALIDATION_ERROR"
    assert code(transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "5", key="")) == "VALIDATION_ERROR"


@pytest.mark.tc("TC-TRF-014")
def test_failure_in_the_middle_of_a_transfer_leaves_no_trace(app, world, monkeypatch):
    """Atomicité : si une écriture échoue avant le commit, ni soldes, ni écritures, ni clé d'idempotence ne changent."""
    from fastapi.testclient import TestClient
    w = world
    client = TestClient(app, raise_server_exceptions=False)
    before = balance(client, w["alice"], w["c1"]["id"])
    original, calls = services._add_tx, {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 4:                      # 4e écriture : TRANSFER_IN du bénéficiaire
            raise RuntimeError("panne simulée")
        return original(*args, **kwargs)

    monkeypatch.setattr(services, "_add_tx", flaky)
    r = transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "100", key="boom")
    assert r.status_code == 500 and code(r) == "INTERNAL_ERROR"
    assert "Traceback" not in r.text and "panne simulée" not in r.text         # pas de fuite de détails internes
    monkeypatch.setattr(services, "_add_tx", original)
    assert balance(client, w["alice"], w["c1"]["id"]) == before
    assert balance(client, w["bob"], w["b1"]["id"]) == 0
    with app.state.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0
        assert db.scalar(select(func.count()).select_from(Transaction).where(Transaction.type.in_(["TRANSFER_OUT", "FEE", "TRANSFER_IN"]))) == 0
        assert db.scalars(select(Account).where(Account.type == "REVENUE")).one().balance == 0
    assert transfer(client, w["alice"], w["c1"]["id"], w["b1"]["iban"], "100", key="boom").status_code == 201  # réessai OK


@pytest.mark.tc("TC-TRF-016")
def test_daily_cap_is_shared_by_withdrawals_and_transfers_and_excludes_fees(client, fake_clock):
    a, b = make_user(client), make_user(client)
    src, dst = open_account(client, a, balance="10000"), open_account(client, b)
    assert withdraw(client, a, src["id"], "2000").status_code == 201
    assert transfer(client, a, src["id"], dst["iban"], "3000").status_code == 201      # 3000 + frais 2 : seuls 3000 comptent
    r = withdraw(client, a, src["id"], "0.001")
    assert r.status_code == 422 and code(r) == "DAILY_LIMIT_EXCEEDED"
    r = transfer(client, a, src["id"], dst["iban"], "0.001")
    assert r.status_code == 422 and code(r) == "DAILY_LIMIT_EXCEEDED"


@pytest.mark.tc("TC-TRF-017")
def test_reference_length_and_hostile_content(client, world):
    w = world
    assert code(transfer(client, w["alice"], w["c1"]["id"], w["c2"]["iban"], "1", reference="r" * 141)) == "VALIDATION_ERROR"
    assert transfer(client, w["alice"], w["c1"]["id"], w["c2"]["iban"], "1", reference="r" * 140).status_code == 201
    payload = "<img src=x onerror=alert(1)>"
    assert transfer(client, w["alice"], w["c1"]["id"], w["c2"]["iban"], "1", reference=payload).status_code == 201
    h = client.get(f"/api/accounts/{w['c2']['id']}/transactions", headers=w["alice"]["headers"])
    assert h.headers["content-type"].startswith("application/json")                    # jamais interprété comme HTML
    assert any(t["reference"] == payload for t in h.json()["items"])


@pytest.mark.tc("TC-TRF-019")
def test_internal_revenue_account_is_unreachable(client, app, world):
    with app.state.SessionLocal() as db:
        revenue = db.scalars(select(Account).where(Account.type == "REVENUE")).one()
        rev_id, rev_iban = revenue.id, revenue.iban
    r = transfer(client, world["alice"], world["c1"]["id"], rev_iban, "1")
    assert r.status_code == 404 and code(r) == "DESTINATION_NOT_FOUND"
    for headers in (world["alice"]["headers"], admin_headers(client)):
        assert client.get(f"/api/accounts/{rev_id}", headers=headers).status_code == 404


@pytest.mark.tc("TC-TRF-020")
def test_cannot_transfer_from_someone_elses_account(client, world):
    w = world
    r = transfer(client, w["bob"], w["c1"]["id"], w["b1"]["iban"], "1")
    assert r.status_code == 404 and code(r) == "ACCOUNT_NOT_FOUND"
    assert balance(client, w["alice"], w["c1"]["id"]) == Decimal("5000")


@pytest.mark.tc("TC-TRF-021")
@pytest.mark.parametrize("body", [
    {"to_iban": "x", "amount": "1"},
    {"from_account_id": 0, "to_iban": "x", "amount": "1"},
    {"from_account_id": 1, "to_iban": "", "amount": "1"},
    {"from_account_id": 1, "to_iban": "x", "amount": "1", "fee": "0"},
])
def test_transfer_payload_validation(client, world, body):
    r = client.post("/api/transfers", json=body, headers=world["alice"]["headers"])
    assert r.status_code == 422 and code(r) == "VALIDATION_ERROR"


@pytest.mark.tc("TC-HIS-003")
def test_deposit_then_transfer_then_history_is_consistent(client, world):
    """balance_after de chaque écriture = solde réel après cette écriture."""
    w = world
    deposit(client, w["alice"], w["c2"]["id"], "10")
    transfer(client, w["alice"], w["c2"]["id"], w["b1"]["iban"], "4")
    items = client.get(f"/api/accounts/{w['c2']['id']}/transactions", headers=w["alice"]["headers"]).json()["items"]
    assert [t["type"] for t in items] == ["FEE", "TRANSFER_OUT", "DEPOSIT"]
    assert [t["balance_after"] for t in items] == ["5.500", "6.000", "10.000"]

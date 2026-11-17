from decimal import Decimal

import pytest

from tests.helpers import admin_headers, balance, code, deposit, make_user, open_account, transfer, withdraw

pytestmark = pytest.mark.api


@pytest.fixture
def busy(client):
    """Un compte avec 25 dépôts de 1,000 puis 2 retraits de 0,500 (27 écritures)."""
    u = make_user(client)
    acc = open_account(client, u)
    for _ in range(25):
        assert deposit(client, u, acc["id"], "1").status_code == 201
    for _ in range(2):
        assert withdraw(client, u, acc["id"], "0.5").status_code == 201
    return u, acc


def _hist(client, u, acc, qs=""):
    return client.get(f"/api/accounts/{acc['id']}/transactions{qs}", headers=u["headers"])


@pytest.mark.tc("TC-HIS-001")
@pytest.mark.parametrize("qs,status,n_items", [
    ("", 200, 20), ("?limit=1", 200, 1), ("?limit=100", 200, 27), ("?limit=20&offset=20", 200, 7),
    ("?offset=27", 200, 0), ("?limit=0", 422, None), ("?limit=101", 422, None), ("?offset=-1", 422, None),
    ("?limit=abc", 422, None),
])
def test_pagination_boundaries(client, busy, qs, status, n_items):
    u, acc = busy
    r = _hist(client, u, acc, qs)
    assert r.status_code == status
    if status == 200:
        assert len(r.json()["items"]) == n_items and r.json()["total"] == 27
    else:
        assert code(r) == "VALIDATION_ERROR"


@pytest.mark.tc("TC-HIS-002")
def test_filter_by_type_and_newest_first(client, busy):
    u, acc = busy
    only = _hist(client, u, acc, "?type=WITHDRAWAL").json()
    assert only["total"] == 2 and {t["type"] for t in only["items"]} == {"WITHDRAWAL"}
    ids = [t["id"] for t in _hist(client, u, acc, "?limit=100").json()["items"]]
    assert ids == sorted(ids, reverse=True)
    assert code(_hist(client, u, acc, "?type=BOGUS")) == "VALIDATION_ERROR"


@pytest.mark.tc("TC-HIS-003")
def test_last_balance_after_equals_current_balance(client, busy):
    u, acc = busy
    newest = _hist(client, u, acc, "?limit=1").json()["items"][0]
    assert Decimal(newest["balance_after"]) == balance(client, u, acc["id"]) == Decimal("24.000")


@pytest.mark.tc("TC-HIS-004")
def test_history_access_control(client, busy):
    u, acc = busy
    other = make_user(client)
    assert _hist(client, other, acc).status_code == 404
    admin = {"headers": admin_headers(client)}
    assert _hist(client, admin, acc, "?limit=1").status_code == 200
    r = client.get(f"/api/accounts/{acc['id']}/transactions")
    assert r.status_code == 401


# ------------------------------------------------------------------ projection d'intérêts


@pytest.mark.tc("TC-SAV-003")
def test_projection_values(client):
    u = make_user(client)
    sav = open_account(client, u, "SAVINGS", "1000")
    r = client.get(f"/api/accounts/{sav['id']}/interest-projection?days=30", headers=u["headers"])
    assert r.status_code == 200
    assert r.json()["projected_interest"] == "2.877" and r.json()["projected_balance"] == "1002.877"
    r = client.get(f"/api/accounts/{sav['id']}/interest-projection?days=365", headers=u["headers"])
    assert r.json()["projected_interest"] == "35.000" and r.json()["annual_rate"] == "0.035"
    default = client.get(f"/api/accounts/{sav['id']}/interest-projection", headers=u["headers"]).json()
    assert default["days"] == 30
    empty = open_account(client, u, "SAVINGS")
    assert client.get(f"/api/accounts/{empty['id']}/interest-projection", headers=u["headers"]).json()["projected_interest"] == "0.000"


@pytest.mark.tc("TC-SAV-004")
@pytest.mark.parametrize("days,status", [(0, 422), (1, 200), (365, 200), (366, 422), (-5, 422), ("abc", 422)])
def test_projection_days_boundaries(client, days, status):
    u = make_user(client)
    sav = open_account(client, u, "SAVINGS", "10")
    assert client.get(f"/api/accounts/{sav['id']}/interest-projection?days={days}", headers=u["headers"]).status_code == status


@pytest.mark.tc("TC-SAV-005")
def test_projection_only_for_open_savings_accounts(client):
    u = make_user(client)
    chk = open_account(client, u, "CHECKING", "10")
    r = client.get(f"/api/accounts/{chk['id']}/interest-projection", headers=u["headers"])
    assert r.status_code == 422 and code(r) == "NOT_A_SAVINGS_ACCOUNT"
    sav = open_account(client, u, "SAVINGS")
    client.post(f"/api/accounts/{sav['id']}/close", headers=u["headers"])
    r = client.get(f"/api/accounts/{sav['id']}/interest-projection", headers=u["headers"])
    assert r.status_code == 409 and code(r) == "ACCOUNT_CLOSED"

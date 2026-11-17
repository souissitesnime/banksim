from decimal import Decimal

import pytest

from tests.helpers import admin_headers, code, make_user, transfer

pytestmark = pytest.mark.api


@pytest.mark.tc("TC-E2E-001")
def test_full_customer_journey(client, fake_clock):
    """Parcours complet (test de cas d'utilisation) : inscription -> comptes -> dépôt -> virement -> historique -> clôture."""
    amira = make_user(client, name="Amira Ben Salah")
    karim = make_user(client, name="Karim Trabelsi")

    chk = client.post("/api/accounts", json={"type": "CHECKING"}, headers=amira["headers"]).json()
    sav = client.post("/api/accounts", json={"type": "SAVINGS"}, headers=amira["headers"]).json()
    kar = client.post("/api/accounts", json={"type": "CHECKING"}, headers=karim["headers"]).json()

    assert client.post(f"/api/accounts/{chk['id']}/deposit", json={"amount": "2000"}, headers=amira["headers"]).status_code == 201
    assert transfer(client, amira, chk["id"], sav["iban"], "800").json()["fee"] == "0.000"          # épargne : gratuit
    r = transfer(client, amira, chk["id"], kar["iban"], "300", key="loyer-nov", reference="Loyer novembre")
    assert r.status_code == 201 and r.json()["fee"] == "0.500"
    assert client.post(f"/api/accounts/{chk['id']}/withdraw", json={"amount": "100"}, headers=amira["headers"]).status_code == 201

    proj = client.get(f"/api/accounts/{sav['id']}/interest-projection?days=30", headers=amira["headers"]).json()
    assert proj["projected_interest"] == "2.301"                                                        # 800 x 3,5 % x 30 / 365

    hist = client.get(f"/api/accounts/{chk['id']}/transactions?limit=100", headers=amira["headers"]).json()
    assert [t["type"] for t in hist["items"]] == ["WITHDRAWAL", "FEE", "TRANSFER_OUT", "TRANSFER_OUT", "DEPOSIT"]
    assert Decimal(hist["items"][0]["balance_after"]) == Decimal("799.500")

    # Soldes finaux, puis vidage et clôture de chaque compte (le plafond journalier de 5 000 n'est pas atteint).
    for acc, owner, expected in ((chk, amira, "799.500"), (sav, amira, "800.000"), (kar, karim, "300.000")):
        bal = client.get(f"/api/accounts/{acc['id']}", headers=owner["headers"]).json()["balance"]
        assert bal == expected
        assert client.post(f"/api/accounts/{acc['id']}/close", headers=owner["headers"]).status_code == 409  # solde non nul
        assert client.post(f"/api/accounts/{acc['id']}/withdraw", json={"amount": bal}, headers=owner["headers"]).status_code == 201
        closed = client.post(f"/api/accounts/{acc['id']}/close", headers=owner["headers"])
        assert closed.status_code == 200 and closed.json()["status"] == "CLOSED"

    assert code(client.get("/api/admin/audit-log", headers=amira["headers"])) == "FORBIDDEN"
    assert client.get("/api/admin/audit-log", headers=admin_headers(client)).json()["total"] > 10

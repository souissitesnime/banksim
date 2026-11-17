"""Démarrage : script de données de démonstration et point d'entrée ASGI."""
import importlib
import sys

import pytest
from sqlalchemy import select

from app.database import make_engine
from app.models import Account, User

pytestmark = pytest.mark.api


@pytest.mark.tc("TC-OPS-001")
def test_seed_creates_demo_customers_once(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{tmp_path / 'seed.db'}"
    monkeypatch.setenv("BANKSIM_DATABASE_URL", url)
    from app import seed
    seed.main()
    seed.main()  # deuxième exécution : aucune duplication
    out = capsys.readouterr().out
    assert "amira@example.com" in out and "karim@example.com" in out
    engine = make_engine(url)
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        assert len(db.scalars(select(User).where(User.role == "CUSTOMER")).all()) == 2
        assert len(db.scalars(select(Account).where(Account.type != "REVENUE")).all()) == 4
    engine.dispose()


@pytest.mark.tc("TC-OPS-002")
def test_asgi_entrypoint_exposes_a_working_app(tmp_path, monkeypatch):
    monkeypatch.setenv("BANKSIM_DATABASE_URL", f"sqlite:///{tmp_path / 'asgi.db'}")
    from fastapi.testclient import TestClient
    sys.modules.pop("app.asgi", None)  # une seule application créée, avec la base temporaire
    module = importlib.import_module("app.asgi")
    with TestClient(module.app) as c:
        assert c.get("/api/health").json()["status"] == "ok"
    module.app.state.engine.dispose()

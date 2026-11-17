"""Fiabilité : accès concurrents. Utilise une base SQLite fichier et de vrais threads (couche service)."""
import threading
import pytest
from sqlalchemy import func, select

from app import services
from app.errors import BankError
from app.models import Account, Transaction, User

pytestmark = [pytest.mark.api, pytest.mark.nonfunctional]


def _setup(tmp_path, make_app):
    app = make_app(f"sqlite:///{tmp_path / 'concurrent.db'}")
    factory = app.state.SessionLocal
    with factory() as db:
        user = services.register_user(db, "Client Concurrent", "c@example.tn", "Abcdef12")
        src = services.create_account(db, user, "CHECKING")
        dst = services.create_account(db, user, "CHECKING")
        services.deposit(db, user, src.id, 1_000_000)  # 1000,000 TND
        return factory, user.id, src.id, dst.id, dst.iban


def _run(threads):
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not any(t.is_alive() for t in threads), "interblocage détecté"


@pytest.mark.tc("TC-TRF-018")
def test_parallel_withdrawals_never_break_the_overdraft_floor(tmp_path, make_app):
    factory, uid, src_id, _, _ = _setup(tmp_path, make_app)
    results = []

    def worker():
        with factory() as db:
            try:
                services.withdraw(db, db.get(User, uid), src_id, 100_000)  # 100,000 TND
                results.append("OK")
            except BankError as exc:
                results.append(exc.code)

    _run([threading.Thread(target=worker) for _ in range(20)])
    # solde 1000 + découvert 500 = 1500 disponibles -> exactement 15 retraits de 100 acceptés
    assert results.count("OK") == 15 and results.count("INSUFFICIENT_FUNDS") == 5
    with factory() as db:
        assert db.get(Account, src_id).balance == -500_000


@pytest.mark.tc("TC-TRF-018")
def test_parallel_requests_with_same_idempotency_key_execute_once(tmp_path, make_app):
    factory, uid, src_id, _, dst_iban = _setup(tmp_path, make_app)
    replayed = []

    def worker():
        with factory() as db:
            _, was_replay = services.transfer(db, db.get(User, uid), src_id, dst_iban, 10_000, None, "same-key")
            replayed.append(was_replay)

    _run([threading.Thread(target=worker) for _ in range(10)])
    assert replayed.count(False) == 1 and replayed.count(True) == 9
    with factory() as db:
        assert db.get(Account, src_id).balance == 990_000
        outs = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.type == "TRANSFER_OUT"))
        assert outs == 1


@pytest.mark.tc("TC-TRF-018")
def test_parallel_registration_with_same_email_creates_one_user(tmp_path, make_app):
    app = make_app(f"sqlite:///{tmp_path / 'reg.db'}")
    factory, outcomes = app.state.SessionLocal, []

    def worker():
        with factory() as db:
            try:
                services.register_user(db, "Jumeau", "twin@example.tn", "Abcdef12")
                outcomes.append("OK")
            except BankError as exc:
                outcomes.append(exc.code)

    _run([threading.Thread(target=worker) for _ in range(6)])
    assert outcomes.count("OK") == 1 and outcomes.count("EMAIL_ALREADY_REGISTERED") == 5
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.email == "twin@example.tn")) == 1

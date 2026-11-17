"""Tests basés sur les propriétés (Hypothesis) : des séquences aléatoires d'opérations ne doivent JAMAIS violer
les invariants comptables, quelle que soit la combinaison de montants et de comptes."""
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import func, select

from app import rules, services
from app.errors import BankError
from app.main import create_app
from app.models import Account, Transaction

pytestmark = pytest.mark.property

OPERATION = st.tuples(
    st.sampled_from(["deposit", "withdraw", "transfer"]),
    st.integers(min_value=0, max_value=3),         # compte source
    st.integers(min_value=0, max_value=3),         # compte destination
    st.integers(min_value=-1_000, max_value=6_000_000),  # millimes : inclut 0, négatifs et valeurs hors plage
)


def _world():
    app = create_app("sqlite://")
    db = app.state.SessionLocal()
    users = [services.register_user(db, f"U{i}", f"u{i}@example.tn", "Abcdef12") for i in range(2)]
    accounts = []
    for u in users:
        accounts.append((u, services.create_account(db, u, "CHECKING")))
        accounts.append((u, services.create_account(db, u, "SAVINGS")))
    return app, db, accounts


@pytest.mark.tc("TC-TRF-015")
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(OPERATION, min_size=1, max_size=25))
def test_money_is_conserved_and_floors_respected(operations):
    app, db, accounts = _world()
    external_in = external_out = 0
    try:
        for kind, i, j, amount in operations:
            user, src = accounts[i]
            try:
                if kind == "deposit":
                    services.deposit(db, user, src.id, amount)
                    external_in += amount
                elif kind == "withdraw":
                    services.withdraw(db, user, src.id, amount)
                    external_out += amount
                else:
                    services.transfer(db, user, src.id, accounts[j][1].iban, amount, None, None)
            except BankError:
                db.rollback()  # opération refusée : aucun effet attendu
        db.expire_all()

        balances = {a.id: a.balance for a in db.scalars(select(Account))}
        # (1) conservation : somme des soldes (frais inclus) = entrées - sorties externes
        assert sum(balances.values()) == external_in - external_out
        # (2) planchers : courant >= -500, épargne >= 0, compte interne >= 0
        for acc in db.scalars(select(Account)):
            floor = rules.OVERDRAFT_FLOOR.get(acc.type, 0)
            assert acc.balance >= floor, (acc.type, acc.balance)
        # (3) le solde de chaque compte = somme de ses écritures
        sums = dict(db.execute(select(Transaction.account_id, func.sum(Transaction.amount)).group_by(Transaction.account_id)).all())
        for acc_id, balance in balances.items():
            assert balance == int(sums.get(acc_id, 0))
        # (4) balance_after de la dernière écriture = solde courant
        for acc_id, balance in balances.items():
            last = db.scalars(select(Transaction).where(Transaction.account_id == acc_id).order_by(Transaction.id.desc())).first()
            if last is not None:
                assert last.balance_after == balance
    finally:
        db.close()
        app.state.engine.dispose()

"""Logique métier. Aucune dépendance HTTP : appelable directement par les tests de composant.

Ordre des contrôles pour une opération d'argent (documenté dans SPEC.md §4.3) :
  authentification (401) -> format du corps (422, avant d'arriver ici) -> propriété du compte (404)
  -> état du compte (409) -> plage du montant (422) -> fonds suffisants (422) -> plafond journalier (422).
"""
from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import clock, money, rules, security
from .config import Settings
from .errors import BankError
from .models import Account, AuditLog, IdempotencyRecord, Transaction, User

# Sérialise les mouvements d'argent dans ce processus (SQLite n'offre pas SELECT ... FOR UPDATE).
# En production : verrouillage de ligne PostgreSQL + contrainte/version optimiste (voir ARCHITECTURE.md, ADR-04).
_MONEY_LOCK = threading.RLock()


# ===================================================================== utilitaires


def _audit(db: Session, actor_id: int | None, action: str, entity: str, entity_id: int | None, **details) -> None:
    db.add(
        AuditLog(
            ts=clock.now(),
            actor_id=actor_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=json.dumps(details, ensure_ascii=False, sort_keys=True),
        )
    )


def _add_tx(db: Session, account: Account, ttype: str, amount: int, counterparty: str | None,
            reference: str | None, transfer_id: str | None, when) -> Transaction:
    tx = Transaction(
        account_id=account.id,
        type=ttype,
        amount=amount,
        balance_after=account.balance,
        counterparty_iban=counterparty,
        reference=reference,
        transfer_id=transfer_id,
        created_at=when,
    )
    db.add(tx)
    return tx


def _get_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None or account.type == "REVENUE":
        raise BankError(404, "ACCOUNT_NOT_FOUND", "Compte introuvable.")
    return account


def _owned_account(db: Session, user: User, account_id: int, allow_admin: bool = False) -> Account:
    """404 (et non 403) si le compte appartient à un autre client : on ne révèle pas son existence."""
    account = _get_account(db, account_id)
    if account.owner_id != user.id and not (allow_admin and user.role == "ADMIN"):
        raise BankError(404, "ACCOUNT_NOT_FOUND", "Compte introuvable.")
    return account


def _require_active(account: Account) -> None:
    if account.status == "FROZEN":
        raise BankError(409, "ACCOUNT_FROZEN", "Ce compte est gelé : les débits sont interdits.")
    if account.status == "CLOSED":
        raise BankError(409, "ACCOUNT_CLOSED", "Ce compte est clôturé.")


def _check_range(amount_m: int, low: int, high: int) -> None:
    if amount_m < low or amount_m > high:
        raise BankError(
            422,
            "AMOUNT_OUT_OF_RANGE",
            f"Le montant doit être compris entre {money.format_millimes(low)} et {money.format_millimes(high)} TND.",
        )


def _outgoing_today(db: Session, account_id: int) -> int:
    start = clock.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    total = db.scalar(
        select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.type.in_(["WITHDRAWAL", "TRANSFER_OUT"]),
            Transaction.created_at >= start,
            Transaction.created_at < end,
        )
    )
    return int(total)


def _revenue_account(db: Session) -> Account:
    return db.scalars(select(Account).where(Account.type == "REVENUE")).one()


def _unique_iban(db: Session) -> str:
    for _ in range(20):
        iban = money.build_iban(money.random_account_number())
        if db.scalar(select(Account.id).where(Account.iban == iban)) is None:
            return iban
    raise RuntimeError("Impossible de générer un IBAN unique.")  # pragma: no cover


# ===================================================================== démarrage


def bootstrap(db: Session, settings: Settings) -> None:
    """Crée le compte interne des frais et l'administrateur initial s'ils n'existent pas."""
    if db.scalar(select(Account.id).where(Account.type == "REVENUE")) is None:
        db.add(Account(owner_id=None, iban=_unique_iban(db), type="REVENUE", status="ACTIVE", balance=0,
                       created_at=clock.now()))
    if db.scalar(select(User.id).where(User.email == settings.admin_email.lower())) is None:
        db.add(User(email=settings.admin_email.lower(), full_name="Administrateur BankSim",
                    password_hash=security.hash_password(settings.admin_password), role="ADMIN",
                    status="ACTIVE", failed_attempts=0, created_at=clock.now()))
    db.commit()


# ===================================================================== authentification


def register_user(db: Session, full_name: str, email: str, password: str) -> User:
    email = email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise BankError(409, "EMAIL_ALREADY_REGISTERED", "Cette adresse e-mail est déjà utilisée.")
    user = User(email=email, full_name=full_name, password_hash=security.hash_password(password),
                role="CUSTOMER", status="ACTIVE", failed_attempts=0, created_at=clock.now())
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # inscription simultanée avec le même e-mail
        db.rollback()
        raise BankError(409, "EMAIL_ALREADY_REGISTERED", "Cette adresse e-mail est déjà utilisée.") from None
    _audit(db, user.id, "USER_REGISTERED", "user", user.id)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> str:
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        security.verify_password(password, security.dummy_hash())  # égalise le temps de réponse
        raise BankError(401, "INVALID_CREDENTIALS", "Identifiants invalides.")
    if user.status == "LOCKED":
        raise BankError(423, "ACCOUNT_LOCKED", "Compte utilisateur verrouillé. Contactez votre conseiller.")
    if not security.verify_password(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= rules.MAX_FAILED_LOGINS:
            user.status = "LOCKED"
            _audit(db, user.id, "USER_LOCKED", "user", user.id, failed_attempts=user.failed_attempts)
            db.commit()
            raise BankError(423, "ACCOUNT_LOCKED", "Trop de tentatives : compte utilisateur verrouillé.")
        _audit(db, user.id, "LOGIN_FAILED", "user", user.id, failed_attempts=user.failed_attempts)
        db.commit()
        raise BankError(401, "INVALID_CREDENTIALS", "Identifiants invalides.")
    user.failed_attempts = 0
    _audit(db, user.id, "LOGIN_SUCCEEDED", "user", user.id)
    db.commit()
    return security.create_token(user.id, user.role)


# ===================================================================== comptes


def create_account(db: Session, user: User, account_type: str) -> Account:
    with _MONEY_LOCK:
        open_count = db.scalar(
            select(func.count()).select_from(Account).where(Account.owner_id == user.id, Account.status != "CLOSED")
        )
        if open_count >= rules.MAX_OPEN_ACCOUNTS:
            raise BankError(409, "ACCOUNT_LIMIT_REACHED",
                            f"Maximum {rules.MAX_OPEN_ACCOUNTS} comptes ouverts par client.")
        account = Account(owner_id=user.id, iban=_unique_iban(db), type=account_type, status="ACTIVE",
                          balance=0, created_at=clock.now())
        db.add(account)
        db.flush()
        _audit(db, user.id, "ACCOUNT_OPENED", "account", account.id, type=account_type)
        db.commit()
        return account


def list_accounts(db: Session, user: User) -> list[Account]:
    return list(db.scalars(select(Account).where(Account.owner_id == user.id).order_by(Account.id.desc())))


def get_account(db: Session, user: User, account_id: int) -> Account:
    return _owned_account(db, user, account_id, allow_admin=True)


def close_account(db: Session, user: User, account_id: int) -> Account:
    with _MONEY_LOCK:
        account = _owned_account(db, user, account_id)
        _require_active(account)
        if account.balance != 0:
            raise BankError(409, "BALANCE_NOT_ZERO", "Le solde doit être égal à 0,000 TND pour clôturer le compte.")
        account.status = "CLOSED"
        _audit(db, user.id, "ACCOUNT_CLOSED", "account", account.id)
        db.commit()
        return account


def set_frozen(db: Session, admin: User, account_id: int, frozen: bool) -> Account:
    """Transitions autorisées : ACTIVE -> FROZEN (gel) et FROZEN -> ACTIVE (dégel). Rien d'autre."""
    with _MONEY_LOCK:
        account = _get_account(db, account_id)
        source, target = ("ACTIVE", "FROZEN") if frozen else ("FROZEN", "ACTIVE")
        if account.status != source:
            raise BankError(409, "INVALID_STATE_TRANSITION",
                            f"Transition impossible : {account.status} -> {target}.")
        account.status = target
        _audit(db, admin.id, "ACCOUNT_FROZEN" if frozen else "ACCOUNT_UNFROZEN", "account", account.id)
        db.commit()
        return account


def unlock_user(db: Session, admin: User, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise BankError(404, "USER_NOT_FOUND", "Utilisateur introuvable.")
    if target.status != "LOCKED":
        raise BankError(409, "USER_NOT_LOCKED", "Cet utilisateur n'est pas verrouillé.")
    target.status = "ACTIVE"
    target.failed_attempts = 0
    _audit(db, admin.id, "USER_UNLOCKED", "user", target.id)
    db.commit()
    return target


# ===================================================================== dépôts / retraits


def deposit(db: Session, user: User, account_id: int, amount_m: int) -> Transaction:
    with _MONEY_LOCK:
        account = _owned_account(db, user, account_id)
        if account.status == "CLOSED":
            raise BankError(409, "ACCOUNT_CLOSED", "Ce compte est clôturé.")
        _check_range(amount_m, rules.DEPOSIT_MIN, rules.DEPOSIT_MAX)
        account.balance += amount_m  # un compte gelé peut encore recevoir de l'argent
        tx = _add_tx(db, account, "DEPOSIT", amount_m, None, None, None, clock.now())
        db.flush()
        _audit(db, user.id, "DEPOSIT", "account", account.id, amount=amount_m)
        db.commit()
        return tx


def withdraw(db: Session, user: User, account_id: int, amount_m: int) -> Transaction:
    with _MONEY_LOCK:
        account = _owned_account(db, user, account_id)
        _require_active(account)
        _check_range(amount_m, rules.WITHDRAW_MIN, rules.WITHDRAW_MAX)
        if account.balance - amount_m < rules.OVERDRAFT_FLOOR[account.type]:
            raise BankError(422, "INSUFFICIENT_FUNDS", "Solde insuffisant.")
        if _outgoing_today(db, account.id) + amount_m > rules.DAILY_OUT_CAP:
            raise BankError(422, "DAILY_LIMIT_EXCEEDED", "Plafond journalier de sorties d'argent dépassé.")
        account.balance -= amount_m
        tx = _add_tx(db, account, "WITHDRAWAL", -amount_m, None, None, None, clock.now())
        db.flush()
        _audit(db, user.id, "WITHDRAWAL", "account", account.id, amount=amount_m)
        db.commit()
        return tx


# ===================================================================== virements


def _request_hash(from_id: int, to_iban: str, amount_m: int, reference: str | None) -> str:
    raw = json.dumps([from_id, to_iban, amount_m, reference], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def transfer(db: Session, user: User, from_account_id: int, to_iban: str, amount_m: int,
             reference: str | None, idempotency_key: str | None) -> tuple[dict, bool]:
    """Retourne (réponse, rejouée?). Atomique : un seul commit à la fin."""
    if idempotency_key is not None and not (1 <= len(idempotency_key) <= 128):
        raise BankError(422, "VALIDATION_ERROR", "Idempotency-Key doit contenir de 1 à 128 caractères.")
    req_hash = _request_hash(from_account_id, to_iban, amount_m, reference)

    with _MONEY_LOCK:
        if idempotency_key is not None:
            record = db.scalar(select(IdempotencyRecord).where(
                IdempotencyRecord.user_id == user.id, IdempotencyRecord.key == idempotency_key))
            if record is not None:
                if record.request_hash != req_hash:
                    raise BankError(409, "IDEMPOTENCY_KEY_REUSED",
                                    "Cette clé d'idempotence a déjà servi pour une autre requête.")
                return json.loads(record.response_json), True

        src = _owned_account(db, user, from_account_id)
        _require_active(src)
        _check_range(amount_m, rules.TRANSFER_MIN, rules.TRANSFER_MAX)
        if not money.is_valid_iban(to_iban):
            raise BankError(422, "INVALID_IBAN", "IBAN destinataire invalide.")
        dest = db.scalar(select(Account).where(Account.iban == to_iban, Account.type != "REVENUE"))
        if dest is None:
            raise BankError(404, "DESTINATION_NOT_FOUND", "Compte destinataire introuvable.")
        if dest.id == src.id:
            raise BankError(422, "SAME_ACCOUNT", "Le compte source et le compte destinataire sont identiques.")
        if dest.status == "CLOSED":
            raise BankError(409, "DESTINATION_CLOSED", "Le compte destinataire est clôturé.")
        same_owner = dest.owner_id == src.owner_id
        if src.type == "SAVINGS" and not same_owner:
            raise BankError(422, "SAVINGS_TRANSFER_RESTRICTED",
                            "Un compte épargne ne peut virer que vers un compte du même client.")
        fee = money.compute_fee(amount_m, same_owner)
        if src.balance - amount_m - fee < rules.OVERDRAFT_FLOOR[src.type]:
            raise BankError(422, "INSUFFICIENT_FUNDS", "Solde insuffisant (frais inclus).")
        if _outgoing_today(db, src.id) + amount_m > rules.DAILY_OUT_CAP:
            raise BankError(422, "DAILY_LIMIT_EXCEEDED", "Plafond journalier de sorties d'argent dépassé.")

        transfer_id = uuid.uuid4().hex
        now = clock.now()
        src.balance -= amount_m
        _add_tx(db, src, "TRANSFER_OUT", -amount_m, dest.iban, reference, transfer_id, now)
        if fee:
            revenue = _revenue_account(db)
            src.balance -= fee
            _add_tx(db, src, "FEE", -fee, None, "Frais de virement", transfer_id, now)
            revenue.balance += fee
            _add_tx(db, revenue, "FEE", fee, src.iban, "Frais de virement", transfer_id, now)
        dest.balance += amount_m
        _add_tx(db, dest, "TRANSFER_IN", amount_m, src.iban, reference, transfer_id, now)

        response = {
            "transfer_id": transfer_id,
            "from_account_id": src.id,
            "to_iban": dest.iban,
            "amount": money.format_millimes(amount_m),
            "fee": money.format_millimes(fee),
            "from_balance_after": money.format_millimes(src.balance),
            "created_at": now.isoformat(),
        }
        if idempotency_key is not None:
            db.add(IdempotencyRecord(user_id=user.id, key=idempotency_key, request_hash=req_hash,
                                     response_json=json.dumps(response), created_at=now))
        _audit(db, user.id, "TRANSFER", "account", src.id, transfer_id=transfer_id, amount=amount_m, fee=fee)
        db.commit()  # point unique de validation : tout ou rien
        return response, False


# ===================================================================== consultation


def list_transactions(db: Session, user: User, account_id: int, limit: int, offset: int,
                      ttype: str | None) -> tuple[list[Transaction], int]:
    account = _owned_account(db, user, account_id, allow_admin=True)
    cond = [Transaction.account_id == account.id]
    if ttype is not None:
        cond.append(Transaction.type == ttype)
    total = db.scalar(select(func.count()).select_from(Transaction).where(*cond))
    items = list(db.scalars(
        select(Transaction).where(*cond).order_by(Transaction.id.desc()).limit(limit).offset(offset)))
    return items, int(total)


def interest_projection(db: Session, user: User, account_id: int, days: int) -> dict:
    account = _owned_account(db, user, account_id)
    if account.type != "SAVINGS":
        raise BankError(422, "NOT_A_SAVINGS_ACCOUNT", "La projection d'intérêts concerne les comptes épargne.")
    if account.status == "CLOSED":
        raise BankError(409, "ACCOUNT_CLOSED", "Ce compte est clôturé.")
    interest = money.compute_interest(account.balance, rules.SAVINGS_ANNUAL_RATE, days)
    return {
        "account_id": account.id,
        "days": days,
        "annual_rate": str(rules.SAVINGS_ANNUAL_RATE),
        "projected_interest": money.format_millimes(interest),
        "projected_balance": money.format_millimes(account.balance + interest),
    }


def list_audit(db: Session, limit: int, offset: int) -> tuple[list[AuditLog], int]:
    total = db.scalar(select(func.count()).select_from(AuditLog))
    items = list(db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)))
    return items, int(total)

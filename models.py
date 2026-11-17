"""Modèle de données (voir le diagramme ER dans docs/ARCHITECTURE.md)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from . import clock


def _now() -> datetime:
    return clock.now()  # résolu à l'exécution : l'horloge des tests est donc prise en compte


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="CUSTOMER")  # CUSTOMER | ADMIN
    status: Mapped[str] = mapped_column(String(10), default="ACTIVE")  # ACTIVE | LOCKED
    failed_attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    iban: Mapped[str] = mapped_column(String(34), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(10))  # CHECKING | SAVINGS | REVENUE (compte interne des frais)
    status: Mapped[str] = mapped_column(String(10), default="ACTIVE")  # ACTIVE | FROZEN | CLOSED
    balance: Mapped[int] = mapped_column(BigInteger, default=0)  # millimes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    type: Mapped[str] = mapped_column(String(15))  # DEPOSIT|WITHDRAWAL|TRANSFER_OUT|TRANSFER_IN|FEE
    amount: Mapped[int] = mapped_column(BigInteger)  # signé : + crédit, - débit (millimes)
    balance_after: Mapped[int] = mapped_column(BigInteger)
    counterparty_iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(140), nullable=True)
    transfer_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_idem_user_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_now)
    actor_id: Mapped[int | None] = mapped_column(nullable=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    entity: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    details: Mapped[str] = mapped_column(Text, default="{}")

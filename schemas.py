"""Schémas d'entrée/sortie (Pydantic). Les montants sortent en chaînes « 1234.500 » (jamais en float)."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from . import money, rules
from .models import Account, Transaction, User

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# Format canonique d'un montant en chaîne : chiffres ASCII, point décimal, 1 à 3 décimales, pas de zéros superflus.
# Le signe « - » est toléré pour que les montants négatifs reçoivent l'erreur métier AMOUNT_OUT_OF_RANGE.
_AMOUNT_RE = re.compile(r"-?(0|[1-9][0-9]{0,11})(\.[0-9]{1,3})?")  # « - » admis : refusé ensuite par la règle de plage


def _strict_amount(value: Any) -> Any:
    """DEF-001 : Decimal() accepte « 1_000 », « 1e2 », « ５ », « +5 »… — inacceptable pour une API bancaire."""
    if isinstance(value, str) and not _AMOUNT_RE.fullmatch(value):
        raise ValueError("Montant invalide : format 123.456 attendu (chiffres 0-9, point décimal, 3 décimales maximum).")
    return value


Amount = Annotated[Decimal, BeforeValidator(_strict_amount), Field(max_digits=15, decimal_places=3, allow_inf_nan=False)]

TransactionType = Literal["DEPOSIT", "WITHDRAWAL", "TRANSFER_OUT", "TRANSFER_IN", "FEE"]


class _Strict(BaseModel):
    # extra="forbid" : empêche l'« assignation de masse » (ex. {"role": "ADMIN"} à l'inscription).
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------------ entrées


class RegisterIn(_Strict):
    full_name: str = Field(max_length=100)
    email: str = Field(max_length=254)
    password: str = Field(max_length=64)

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Le nom ne peut pas être vide.")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Adresse e-mail invalide.")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
        if not (re.search(r"[a-z]", v) and re.search(r"[A-Z]", v) and re.search(r"[0-9]", v)):
            raise ValueError("Le mot de passe doit contenir une minuscule, une majuscule et un chiffre.")
        return v


class LoginIn(_Strict):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class AccountCreateIn(_Strict):
    type: Literal["CHECKING", "SAVINGS"]


class AmountIn(_Strict):
    amount: Amount


class TransferIn(_Strict):
    from_account_id: int = Field(gt=0)
    to_iban: str = Field(min_length=1, max_length=40)
    amount: Amount
    reference: str | None = Field(default=None, max_length=140)

    @field_validator("to_iban")
    @classmethod
    def _iban(cls, v: str) -> str:
        return money.normalize_iban(v)


# ------------------------------------------------------------------ sorties


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountOut(BaseModel):
    id: int
    iban: str
    type: str
    status: str
    balance: str
    currency: str = rules.CURRENCY
    created_at: datetime


class TransactionOut(BaseModel):
    id: int
    account_id: int
    type: str
    amount: str
    balance_after: str
    counterparty_iban: str | None
    reference: str | None
    transfer_id: str | None
    created_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int


class ProjectionOut(BaseModel):
    account_id: int
    days: int
    annual_rate: str
    projected_interest: str
    projected_balance: str


def user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, full_name=u.full_name, role=u.role)


def account_out(a: Account) -> AccountOut:
    return AccountOut(
        id=a.id,
        iban=a.iban,
        type=a.type,
        status=a.status,
        balance=money.format_millimes(a.balance),
        created_at=a.created_at,
    )


def transaction_out(t: Transaction) -> TransactionOut:
    return TransactionOut(
        id=t.id,
        account_id=t.account_id,
        type=t.type,
        amount=money.format_millimes(t.amount),
        balance_after=money.format_millimes(t.balance_after),
        counterparty_iban=t.counterparty_iban,
        reference=t.reference,
        transfer_id=t.transfer_id,
        created_at=t.created_at,
    )

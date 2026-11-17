"""Fonctions pures : montants (millimes), frais, intérêts, IBAN tunisien fictif.

Ces fonctions n'ont aucune dépendance (base, HTTP) : idéales pour les tests unitaires
(partitions d'équivalence, valeurs limites, couverture des instructions/branches).
"""
from __future__ import annotations

import re
import secrets
from decimal import ROUND_HALF_UP, Decimal

from . import rules

# ---------------------------------------------------------------- montants


def to_millimes(amount: Decimal) -> int:
    """Convertit un Decimal en entier de millimes. Refuse plus de 3 décimales."""
    scaled = amount * 1000
    if scaled != scaled.to_integral_value():
        raise ValueError("Un montant en TND a au plus 3 décimales (millimes).")
    return int(scaled)


def format_millimes(millimes: int) -> str:
    """12500 -> '12.500' ; -300 -> '-0.300'."""
    sign = "-" if millimes < 0 else ""
    m = abs(millimes)
    return f"{sign}{m // 1000}.{m % 1000:03d}"


# ---------------------------------------------------------------- frais & intérêts


def compute_fee(amount_m: int, same_owner: bool) -> int:
    """Frais d'un virement (millimes). Gratuit entre comptes d'un même client."""
    if same_owner:
        return 0
    if amount_m <= rules.FEE_THRESHOLD:
        return rules.FEE_LOW
    return rules.FEE_HIGH


def compute_interest(balance_m: int, annual_rate: Decimal, days: int) -> int:
    """Intérêts simples = solde × taux × jours / 365, arrondis au millime (demi supérieur)."""
    if days < rules.PROJECTION_MIN_DAYS or days > rules.PROJECTION_MAX_DAYS:
        raise ValueError("days doit être compris entre 1 et 365.")
    if balance_m <= 0:
        return 0
    raw = Decimal(balance_m) * annual_rate * Decimal(days) / Decimal(365)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------- IBAN (format TN, clé RIB simplifiée)

COUNTRY = "TN"
BANK_CODE = "99"  # code banque fictif
BRANCH_CODE = "001"
_IBAN_RE = re.compile(r"^TN[0-9]{22}$")  # [0-9] et non \d : \d accepte les chiffres Unicode (DEF-002)


def _letters_to_digits(text: str) -> str:
    return "".join(str(int(ch, 36)) for ch in text)  # A=10 ... Z=35


def normalize_iban(iban: str) -> str:
    return re.sub(r"\s+", "", iban).upper()


def rib_key(account_number: str) -> str:
    """Clé nationale SIMPLIFIÉE (complément à 97) — fictive, non conforme à la clé RIB officielle."""
    n = int(BANK_CODE + BRANCH_CODE + account_number + "00")
    return f"{97 - n % 97:02d}"


def iban_check_digits(bban: str) -> str:
    rearranged = _letters_to_digits(bban + COUNTRY + "00")
    return f"{98 - int(rearranged) % 97:02d}"


def build_iban(account_number: str) -> str:
    """account_number : 13 chiffres -> IBAN de 24 caractères (TN + 2 + 20)."""
    if not re.fullmatch(r"[0-9]{13}", account_number):
        raise ValueError("Le numéro de compte doit contenir 13 chiffres.")
    bban = BANK_CODE + BRANCH_CODE + account_number + rib_key(account_number)
    return COUNTRY + iban_check_digits(bban) + bban


def random_account_number() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(13))


def is_valid_iban(iban: str) -> bool:
    """Format TN + 22 chiffres et contrôle modulo 97 (ISO 13616)."""
    iban = normalize_iban(iban)
    if not _IBAN_RE.match(iban):
        return False
    rearranged = _letters_to_digits(iban[4:] + iban[:4])
    return int(rearranged) % 97 == 1

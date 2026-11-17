"""Règles métier (SPEC.md §4). Tous les montants sont en millimes : 1 TND = 1000 millimes."""
from decimal import Decimal

CURRENCY = "TND"

DEPOSIT_MIN = 1  # 0,001 TND
DEPOSIT_MAX = 50_000_000  # 50 000,000 TND
WITHDRAW_MIN = 1
WITHDRAW_MAX = 2_000_000  # 2 000,000 TND par opération
TRANSFER_MIN = 1
TRANSFER_MAX = 3_000_000  # 3 000,000 TND par virement
DAILY_OUT_CAP = 5_000_000  # retraits + virements sortants (hors frais) par jour UTC

# Solde plancher autorisé selon le type de compte (découvert autorisé sur le compte courant).
OVERDRAFT_FLOOR = {"CHECKING": -500_000, "SAVINGS": 0}

MAX_OPEN_ACCOUNTS = 5

# Frais de virement vers un autre client : 0,500 TND jusqu'à 1 000,000 TND inclus, 2,000 TND au-delà.
FEE_THRESHOLD = 1_000_000
FEE_LOW = 500
FEE_HIGH = 2_000

SAVINGS_ANNUAL_RATE = Decimal("0.035")  # 3,5 % / an, intérêts simples
PROJECTION_MIN_DAYS = 1
PROJECTION_MAX_DAYS = 365

MAX_FAILED_LOGINS = 3

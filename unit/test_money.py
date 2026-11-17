from decimal import Decimal

import pytest

from app import money, rules

pytestmark = pytest.mark.unit


@pytest.mark.tc("TC-MON-001")
@pytest.mark.parametrize("text,expected", [
    ("0", 0), ("0.001", 1), ("1", 1000), ("12.5", 12_500), ("50000.000", 50_000_000), ("-0.300", -300), ("1E-3", 1),
])
def test_to_millimes_ok(text, expected):
    assert money.to_millimes(Decimal(text)) == expected


@pytest.mark.tc("TC-MON-001")
@pytest.mark.parametrize("text", ["0.0001", "1.2345", "-0.0005"])
def test_to_millimes_rejects_more_than_three_decimals(text):
    with pytest.raises(ValueError):
        money.to_millimes(Decimal(text))


@pytest.mark.tc("TC-MON-002")
@pytest.mark.parametrize("millimes,text", [
    (0, "0.000"), (1, "0.001"), (999, "0.999"), (1000, "1.000"), (12_500, "12.500"),
    (-300, "-0.300"), (-1000, "-1.000"), (50_000_000, "50000.000"),
])
def test_format_millimes(millimes, text):
    assert money.format_millimes(millimes) == text


@pytest.mark.tc("TC-MON-002")
def test_format_then_parse_roundtrip():
    for m in (0, 1, 7, 1000, 123_456, -42):
        assert money.to_millimes(Decimal(money.format_millimes(m))) == m


@pytest.mark.tc("TC-FEE-001")
@pytest.mark.parametrize("amount,same_owner,fee", [
    (1, True, 0), (3_000_000, True, 0),              # même client : gratuit
    (1, False, 500), (999_999, False, 500),          # <= seuil : 0,500
    (1_000_000, False, 500),                         # valeur limite haute incluse
    (1_000_001, False, 2_000), (3_000_000, False, 2_000),  # > seuil : 2,000
])
def test_compute_fee(amount, same_owner, fee):
    assert money.compute_fee(amount, same_owner) == fee


@pytest.mark.tc("TC-SAV-001")
@pytest.mark.parametrize("balance,rate,days,expected", [
    (100_000, Decimal("0.035"), 30, 288),        # 0,2877 TND -> 0,288
    (1_000_000, Decimal("0.035"), 365, 35_000),  # une année complète
    (365, Decimal("0.5"), 1, 1),                 # 0,5 -> 1 (demi supérieur)
    (1_825, Decimal("0.5"), 1, 3),               # 2,5 -> 3 (et non 2 : pas d'arrondi bancaire)
    (0, Decimal("0.035"), 30, 0),                # solde nul
    (-5_000, Decimal("0.035"), 30, 0),           # solde négatif : pas d'intérêts
])
def test_compute_interest(balance, rate, days, expected):
    assert money.compute_interest(balance, rate, days) == expected


@pytest.mark.tc("TC-SAV-002")
@pytest.mark.parametrize("days", [0, -1, 366])
def test_compute_interest_days_out_of_range(days):
    with pytest.raises(ValueError):
        money.compute_interest(1000, rules.SAVINGS_ANNUAL_RATE, days)


@pytest.mark.tc("TC-SAV-002")
@pytest.mark.parametrize("days", [1, 365])
def test_compute_interest_days_boundaries_accepted(days):
    assert money.compute_interest(1_000_000, rules.SAVINGS_ANNUAL_RATE, days) > 0

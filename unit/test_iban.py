import re

import pytest

from app import money

pytestmark = pytest.mark.unit


@pytest.mark.tc("TC-IBAN-001")
def test_build_iban_structure():
    iban = money.build_iban("0000000000001")
    assert len(iban) == 24 and iban.startswith("TN") and re.fullmatch(r"TN\d{22}", iban)
    assert iban[4:6] == money.BANK_CODE and iban[6:9] == money.BRANCH_CODE
    assert money.is_valid_iban(iban)


@pytest.mark.tc("TC-IBAN-001")
def test_generated_ibans_are_always_valid():
    for _ in range(200):
        assert money.is_valid_iban(money.build_iban(money.random_account_number()))


@pytest.mark.tc("TC-IBAN-001")
@pytest.mark.parametrize("bad", ["123", "12345678901234", "ABCDEFGHIJKLM", "", "000000000000a"])
def test_build_iban_rejects_bad_account_number(bad):
    with pytest.raises(ValueError):
        money.build_iban(bad)


@pytest.mark.tc("TC-IBAN-002")
def test_checksum_helper_against_public_reference_iban():
    # IBAN public de référence (GB82 WEST 1234 5698 7654 32) : le réarrangement + modulo 97 doit donner 1.
    assert int(money._letters_to_digits("WEST12345698765432GB82")) % 97 == 1


@pytest.mark.tc("TC-IBAN-002")
def test_is_valid_iban_partitions():
    good = money.build_iban("1234567890123")
    flipped = good[:-1] + str((int(good[-1]) + 1) % 10)  # un chiffre modifié -> contrôle modulo 97 en échec
    assert money.is_valid_iban(good)
    assert not money.is_valid_iban(flipped)
    assert not money.is_valid_iban(good[:-1])            # trop court (23)
    assert not money.is_valid_iban(good + "0")           # trop long (25)
    assert not money.is_valid_iban("FR" + good[2:])      # mauvais pays
    assert not money.is_valid_iban("TN" + "A" * 22)      # lettres au lieu de chiffres
    assert not money.is_valid_iban("")


@pytest.mark.tc("TC-IBAN-003")
def test_iban_normalization_accepts_spaces_and_lowercase():
    good = money.build_iban("1234567890123")
    spaced = " ".join(good[i:i + 4] for i in range(0, len(good), 4)).lower()
    assert money.normalize_iban(spaced) == good
    assert money.is_valid_iban(spaced)


@pytest.mark.tc("TC-IBAN-004")
def test_unicode_digits_are_not_valid_iban_digits():
    """DEF-002 (corrigé) : \\d acceptait les chiffres arabes-indiens ; l'IBAN « validé » ne correspondait à aucun compte."""
    good = money.build_iban("1234567890123")
    arabic = good[:2] + good[2:].translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
    fullwidth = good[:2] + good[2:].translate(str.maketrans("0123456789", "０１２３４５６７８９"))
    assert not money.is_valid_iban(arabic) and not money.is_valid_iban(fullwidth)
    with pytest.raises(ValueError):
        money.build_iban("١٢٣٤٥٦٧٨٩٠١٢٣")

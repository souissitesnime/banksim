import time

import jwt
import pytest

from app import security
from app.config import get_settings

pytestmark = [pytest.mark.unit, pytest.mark.security]


@pytest.mark.tc("TC-SEC-001")
def test_hash_is_salted_and_verifiable():
    h1, h2 = security.hash_password("Abcdef12"), security.hash_password("Abcdef12")
    assert h1 != h2                      # sels différents -> empreintes différentes
    assert "Abcdef12" not in h1
    assert h1.startswith("pbkdf2_sha256$")
    assert security.verify_password("Abcdef12", h1)
    assert not security.verify_password("abcdef12", h1)


@pytest.mark.tc("TC-SEC-001")
@pytest.mark.parametrize("stored", ["", "garbage", "md5$1$a$b", "pbkdf2_sha256$x$y$z", "a$b$c$d$e"])
def test_verify_password_with_malformed_hash_is_false(stored):
    assert security.verify_password("Abcdef12", stored) is False


@pytest.mark.tc("TC-AUTH-020")
def test_token_roundtrip_and_claims():
    payload = security.decode_token(security.create_token(7, "CUSTOMER"))
    assert payload["sub"] == "7" and payload["role"] == "CUSTOMER"
    assert payload["exp"] > time.time()


@pytest.mark.tc("TC-AUTH-020")
def test_expired_token_is_rejected():
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(security.create_token(7, "CUSTOMER", ttl_minutes=-1))


@pytest.mark.tc("TC-AUTH-021")
def test_token_signed_with_other_secret_is_rejected():
    forged = jwt.encode({"sub": "1", "exp": time.time() + 600}, "another-secret-another-secret-0123456789", algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        security.decode_token(forged)


@pytest.mark.tc("TC-SEC-005")
def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("BANKSIM_TOKEN_TTL_MINUTES", "5")
    assert get_settings().token_ttl_minutes == 5

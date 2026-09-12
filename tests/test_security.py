from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.core.config import settings
from jose import jwt


def test_password_hash_and_verify_roundtrip():
    plain = "S3curePass!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_contains_expected_claims():
    token = create_access_token(data={"sub": "user@example.com", "role": "admin"})
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "user@example.com"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_refresh_token_hash_is_deterministic_and_raw_token_is_not_the_hash():
    raw, token_hash, expires_at = generate_refresh_token()
    assert raw != token_hash
    assert hash_refresh_token(raw) == token_hash
    # Two generated tokens should never collide in practice (128+ bits of entropy)
    raw2, hash2, _ = generate_refresh_token()
    assert raw != raw2
    assert token_hash != hash2

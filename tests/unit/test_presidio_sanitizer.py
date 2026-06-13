import pytest
from sentry_adapter.infrastructure.presidio_sanitizer import PresidioSanitizer


@pytest.fixture(scope="session")
def sanitizer():
    # en_core_web_sm is enough for tests
    return PresidioSanitizer(
        entities=["EMAIL_ADDRESS", "IP_ADDRESS"],
        secrets_regex=True,
        nlp_model="en_core_web_sm",
    )


async def test_email_is_masked(sanitizer):
    result = await sanitizer.clean("Contact alice@example.com for support")
    assert "alice@example.com" not in result.text
    assert "EMAIL_ADDRESS" in result.detected


async def test_ip_is_masked(sanitizer):
    result = await sanitizer.clean("Request from 192.168.1.1 failed")
    assert "192.168.1.1" not in result.text
    assert "IP_ADDRESS" in result.detected


async def test_jwt_is_masked(sanitizer):
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    result = await sanitizer.clean(f"Authorization: Bearer {jwt}")
    assert jwt not in result.text
    assert "JWT" in result.detected or "BEARER_TOKEN" in result.detected


async def test_github_token_is_masked(sanitizer):
    token = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456789"
    result = await sanitizer.clean(f"token={token}")
    assert token not in result.text
    assert "GITHUB_TOKEN" in result.detected


async def test_clean_text_unchanged(sanitizer):
    text = "ZeroDivisionError: division by zero in calculate()"
    result = await sanitizer.clean(text)
    assert result.text == text
    assert result.detected == []


async def test_empty_string(sanitizer):
    result = await sanitizer.clean("")
    assert result.text == ""
    assert result.detected == []


async def test_multiple_pii_detected(sanitizer):
    text = "User alice@corp.com from 10.0.0.1 logged in"
    result = await sanitizer.clean(text)
    assert "alice@corp.com" not in result.text
    assert "10.0.0.1" not in result.text
    assert "EMAIL_ADDRESS" in result.detected
    assert "IP_ADDRESS" in result.detected

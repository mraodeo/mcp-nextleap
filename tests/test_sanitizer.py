"""
Unit tests for PIISanitizer.
Validates zero-retention redaction and edge cases from edge-case.md.
"""
from src.sanitizer import PIISanitizer

def test_clean_input_no_pii():
    text = "Why was I charged an exit load on HDFC Large Cap Fund?"
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert sanitized == text
    assert artifact["has_pii"] is False
    assert len(artifact["detected_types"]) == 0

def test_standard_pan_redaction():
    text = "My PAN number is ABCDE1234F, please check my account."
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "ABCDE1234F" not in sanitized
    assert "[REDACTED_PAN]" in sanitized
    assert "PAN" in artifact["detected_types"]
    assert artifact["has_pii"] is True

def test_spaced_pan_redaction():
    text = "PAN is A B C D E 1 2 3 4 F."
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "A B C D E 1 2 3 4 F" not in sanitized
    assert "[REDACTED_PAN]" in sanitized
    assert "PAN" in artifact["detected_types"]

def test_aadhaar_redaction():
    text = "My Aadhaar is 2345 6789 0123."
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "2345 6789 0123" not in sanitized
    assert "[REDACTED_AADHAAR]" in sanitized
    assert "AADHAAR" in artifact["detected_types"]

def test_phone_number_redaction():
    text = "Call me at +91 9876543210 or 08765432100 immediately."
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "9876543210" not in sanitized
    assert "8765432100" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "PHONE" in artifact["detected_types"]

def test_spaced_phone_redaction():
    text = "Contact 9 8 7 6 5 4 3 2 1 0."
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "9 8 7 6 5 4 3 2 1 0" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "PHONE" in artifact["detected_types"]

def test_email_redaction():
    text = "Send confirmation to user.test@example.co.in please."
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "user.test@example.co.in" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized
    assert "EMAIL" in artifact["detected_types"]

def test_otp_redaction():
    text = "The OTP received was 482910."
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "482910" not in sanitized
    assert "[REDACTED_OTP]" in sanitized
    assert "OTP" in artifact["detected_types"]

def test_multi_pii_payload():
    text = (
        "Rajesh here, PAN: ABCDE1234F, mobile: 9876543210, "
        "email: rajesh@example.com, Aadhaar: 3456 7890 1234, OTP: 123456."
    )
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "ABCDE1234F" not in sanitized
    assert "9876543210" not in sanitized
    assert "rajesh@example.com" not in sanitized
    assert "3456 7890 1234" not in sanitized
    assert "123456" not in sanitized
    assert set(artifact["detected_types"]) == {"PAN", "PHONE", "EMAIL", "AADHAAR", "OTP"}

def test_false_positive_currency_preservation():
    text = "I invested Rs 10000000 in HDFC Large Cap Fund with NAV 1217.44 on 2026-06-25."
    sanitized, artifact = PIISanitizer.sanitize(text)
    assert "10000000" in sanitized
    assert "1217.44" in sanitized

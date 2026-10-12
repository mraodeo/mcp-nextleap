"""
Deterministic PII Sanitization & Redaction Engine.
Enforces zero-retention compliance across PAN, Aadhaar, Phone, Email, OTP, and Bank Accounts.
"""
import re
from typing import Tuple, List
from src.state import PIIArtifact

class PIISanitizer:
    # 1. Indian Permanent Account Number (PAN)
    # Standard: 5 uppercase letters, 4 digits, 1 uppercase letter
    # Spaced/Hyphenated: e.g. "A B C D E 1 2 3 4 F"
    PAN_STANDARD_PATTERN = re.compile(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}\b")
    PAN_SPACED_PATTERN = re.compile(
        r"\b[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[0-9]\s+[0-9]\s+[0-9]\s+[0-9]\s+[A-Za-z]\b"
    )

    # 2. Aadhaar Number (12 digits, optional spaces/hyphens, starting with 2-9)
    AADHAAR_PATTERN = re.compile(r"\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b")

    # 3. Indian Phone Number (10 digits starting with 6-9, optional +91/0 prefix, handles spaces/hyphens)
    PHONE_STANDARD_PATTERN = re.compile(r"(?:(?:\+91|0)?[-\s]?)?[6-9]\d{4}[-\s]?\d{5}\b")
    PHONE_SPACED_PATTERN = re.compile(r"(?:(?:\+?91|0)[\s-]?)?[6-9](?:\s+[0-9]){9}\b")

    # 4. Email Address (RFC 5322 compatible)
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    # 5. OTP / Verification Code (4-6 digits preceded by keyword with optional words like 'is', 'was', 'received')
    OTP_PATTERN = re.compile(r"\b(?:otp|code|pin|password)(?:[^\d]{0,25})(\b\d{4,6}\b)", re.IGNORECASE)

    # 6. Bank / Demat Account (9 to 18 consecutive digits)
    ACCOUNT_PATTERN = re.compile(r"\b[0-9]{9,18}\b")
    CURRENCY_OR_CODE_PREFIX = re.compile(r"(?:Rs\.?|₹|INR|\$|Order|Txn|ID|id)\s*$", re.IGNORECASE)

    @classmethod
    def sanitize(cls, text: str) -> Tuple[str, PIIArtifact]:
        """
        Scans and redacts all PII instances with strict precedence.
        Returns sanitized text and PII metadata.
        """
        if not text:
            return "", {
                "has_pii": False,
                "detected_types": [],
                "redacted_text": ""
            }

        detected_types: List[str] = []
        sanitized = text

        # 1. Check & Redact PAN (Spaced first, then Standard)
        if cls.PAN_SPACED_PATTERN.search(sanitized):
            detected_types.append("PAN")
            sanitized = cls.PAN_SPACED_PATTERN.sub("[REDACTED_PAN]", sanitized)

        if cls.PAN_STANDARD_PATTERN.search(sanitized):
            detected_types.append("PAN")
            sanitized = cls.PAN_STANDARD_PATTERN.sub("[REDACTED_PAN]", sanitized)

        # 2. Check & Redact Aadhaar
        if cls.AADHAAR_PATTERN.search(sanitized):
            detected_types.append("AADHAAR")
            sanitized = cls.AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", sanitized)

        # 3. Check & Redact Phone (Spaced first, then Standard)
        if cls.PHONE_SPACED_PATTERN.search(sanitized):
            detected_types.append("PHONE")
            sanitized = cls.PHONE_SPACED_PATTERN.sub("[REDACTED_PHONE]", sanitized)

        if cls.PHONE_STANDARD_PATTERN.search(sanitized):
            detected_types.append("PHONE")
            sanitized = cls.PHONE_STANDARD_PATTERN.sub("[REDACTED_PHONE]", sanitized)

        # 4. Check & Redact Emails
        if cls.EMAIL_PATTERN.search(sanitized):
            detected_types.append("EMAIL")
            sanitized = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)

        # 5. Check & Redact OTP
        if cls.OTP_PATTERN.search(sanitized):
            detected_types.append("OTP")
            sanitized = cls.OTP_PATTERN.sub(
                lambda m: m.group(0).replace(m.group(1), "[REDACTED_OTP]"),
                sanitized
            )

        # 6. Check & Redact Bank/Demat Accounts (after phone/aadhaar/otp to avoid collisions)
        def _replace_account(match: re.Match) -> str:
            start = match.start()
            prefix = sanitized[max(0, start - 15):start]
            if cls.CURRENCY_OR_CODE_PREFIX.search(prefix):
                return match.group(0)  # Preserve currency or transaction identifier
            detected_types.append("ACCOUNT")
            return "[REDACTED_ACCOUNT]"

        sanitized = cls.ACCOUNT_PATTERN.sub(_replace_account, sanitized)

        unique_types = sorted(list(set(detected_types)))

        artifact: PIIArtifact = {
            "has_pii": len(unique_types) > 0,
            "detected_types": unique_types,
            "redacted_text": sanitized
        }

        return sanitized, artifact

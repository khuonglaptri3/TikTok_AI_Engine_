"""Typed bounded domain exceptions across packages and API routes."""

from __future__ import annotations

from packages.common.logging import redact_secrets


class ViralRagError(Exception):
    """Base domain error with machine-readable code, HTTP status, and secret-safe message."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        clean_code = code.strip()
        if not clean_code:
            raise ValueError("ViralRagError code must be non-empty")
        safe_message = redact_secrets(message.strip()) or clean_code
        super().__init__(safe_message)
        self.code = clean_code
        self.message = safe_message
        self.status_code = status_code


class CorpusNotReadyError(ViralRagError):
    def __init__(self, message: str) -> None:
        super().__init__("CORPUS_NOT_READY", message, status_code=503)


class IndexNotReadyError(ViralRagError):
    def __init__(self, message: str) -> None:
        super().__init__("INDEX_NOT_READY", message, status_code=503)


class ProviderKeyMissingError(ViralRagError):
    def __init__(self, message: str = "GEMINI_API_KEY is not configured in .env") -> None:
        super().__init__("PROVIDER_KEY_MISSING", message, status_code=503)


class QuotaBlockedError(ViralRagError):
    def __init__(self, message: str) -> None:
        super().__init__("QUOTA_BLOCKED", message, status_code=429)


class UnsupportedDomainError(ViralRagError):
    def __init__(self, message: str) -> None:
        super().__init__("UNSUPPORTED_DOMAIN", message, status_code=422)

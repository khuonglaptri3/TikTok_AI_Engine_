from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from packages.common.logging import redact_secrets
from packages.data_contracts._validators import require_non_blank


class CanonicalErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    code: str
    message: str
    request_id: str | None = None

    @field_validator("code")
    @classmethod
    def _validate_code(cls, val: str) -> str:
        return require_non_blank(val)

    @field_validator("message")
    @classmethod
    def _validate_message(cls, val: str) -> str:
        return redact_secrets(require_non_blank(val))

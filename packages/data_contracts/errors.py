from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CanonicalErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    request_id: str | None = None

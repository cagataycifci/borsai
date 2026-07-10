"""Request/response schemas for the settings & secrets API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SettingItem(BaseModel):
    key: str
    value: Any


class SettingUpdate(BaseModel):
    value: Any


class SecretUpdate(BaseModel):
    api_key: str = Field(min_length=1, description="Provider API key (stored encrypted)")


class SecretStatus(BaseModel):
    """Write-only secrets: we only ever report whether a key is configured."""

    provider: str
    configured: bool


class SecretVerifyRequest(BaseModel):
    api_key: str | None = Field(
        default=None,
        description="Key to test. When omitted, uses the stored key for the provider.",
    )


class SecretVerifyResult(BaseModel):
    provider: str
    ok: bool
    message: str


class ProviderOrder(BaseModel):
    order: list[str] = Field(description="Data provider fallback order")

"""Settings & secrets API routes.

Secrets are write-only: clients can set or clear a provider key and query whether
one is configured, but the plaintext key is never returned.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.settings.schemas import (
    ProviderOrder,
    SecretStatus,
    SecretUpdate,
    SecretVerifyRequest,
    SecretVerifyResult,
    SettingItem,
    SettingUpdate,
)
from app.settings.service import KNOWN_PROVIDERS, SecretsService, SettingsService
from app.settings.validation import verify_provider_key

from .deps import get_secrets_service, get_settings_service

router = APIRouter(prefix="/api/v1")

SettingsDep = Annotated[SettingsService, Depends(get_settings_service)]
SecretsDep = Annotated[SecretsService, Depends(get_secrets_service)]


# ---- Settings --------------------------------------------------------------
@router.get("/settings", response_model=list[SettingItem], summary="All settings")
def list_settings(service: SettingsDep) -> list[SettingItem]:
    return [SettingItem(key=k, value=v) for k, v in service.all().items()]


@router.get("/settings/{key}", response_model=SettingItem, summary="Get a setting")
def get_setting(service: SettingsDep, key: str) -> SettingItem:
    sentinel = object()
    value = service.get(key, sentinel)
    if value is sentinel:
        raise HTTPException(status_code=404, detail=f"No setting '{key}'")
    return SettingItem(key=key, value=value)


@router.put("/settings/{key}", response_model=SettingItem, summary="Set a setting")
def set_setting(service: SettingsDep, key: str, body: SettingUpdate) -> SettingItem:
    service.set(key, body.value)
    return SettingItem(key=key, value=body.value)


@router.get("/providers/order", response_model=ProviderOrder, summary="Data provider order")
def get_provider_order(service: SettingsDep) -> ProviderOrder:
    return ProviderOrder(order=service.get_provider_order())


@router.put("/providers/order", response_model=ProviderOrder, summary="Set provider order")
def set_provider_order(service: SettingsDep, body: ProviderOrder) -> ProviderOrder:
    return ProviderOrder(order=service.set_provider_order(body.order))


# ---- Secrets (write-only) --------------------------------------------------
@router.get("/secrets", response_model=list[SecretStatus], summary="Secret status (all)")
def list_secrets(service: SecretsDep) -> list[SecretStatus]:
    return [SecretStatus(provider=p, configured=c) for p, c in service.status().items()]


@router.put("/secrets/{provider}", response_model=SecretStatus, summary="Set a provider key")
def set_secret(service: SecretsDep, provider: str, body: SecretUpdate) -> SecretStatus:
    if provider not in KNOWN_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    service.set(provider, body.api_key)
    return SecretStatus(provider=provider, configured=True)


@router.delete("/secrets/{provider}", response_model=SecretStatus, summary="Clear a provider key")
def delete_secret(service: SecretsDep, provider: str) -> SecretStatus:
    service.delete(provider)
    return SecretStatus(provider=provider, configured=False)


@router.post(
    "/secrets/{provider}/verify",
    response_model=SecretVerifyResult,
    summary="Test a provider API key (stored or supplied)",
)
async def verify_secret(
    service: SecretsDep,
    provider: str,
    body: SecretVerifyRequest | None = None,
) -> SecretVerifyResult:
    if provider not in KNOWN_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    api_key = (body.api_key if body and body.api_key else None) or service.get(provider)
    ok, message = await verify_provider_key(provider, api_key)
    return SecretVerifyResult(provider=provider, ok=ok, message=message)

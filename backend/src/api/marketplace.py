"""Public marketplace status, per-agent state, and quote preview APIs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.services.algorand import get_algorand_service
from src.services.protocol_config import (
    BASE_PRICE,
    BUY_FEE_BPS,
    CORTEX_ASSET_ID,
    CREATION_FEE,
    FACTORY_APP_ID,
    GRADUATION_THRESHOLD,
    LEGACY_DEPLOYMENTS,
    PROTOCOL_CONFIG,
    SELL_FEE_BPS,
    SLOPE,
    TOKEN_DECIMALS,
)

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


class MarketplaceConfigResponse(BaseModel):
    trading_enabled: bool
    launch_enabled: bool
    maintenance_reason: str | None = None
    active_factory_app_id: int
    deprecated_factory_app_id: int
    legacy_factory_app_ids: list[int]
    cortex_asset_id: int
    creation_fee: int
    buy_fee_bps: int
    sell_fee_bps: int
    graduation_threshold: int
    base_price: int
    slope: int
    next_deployment: dict
    notes: list[str]


class AgentCurveConfig(BaseModel):
    base_price: int
    slope: int
    buy_fee_bps: int
    sell_fee_bps: int
    graduation_threshold: int


class AgentStateResponse(BaseModel):
    asset_id: int
    supply: int
    config: AgentCurveConfig


class QuotePreviewResponse(BaseModel):
    asset_id: int
    amount: int
    current_supply: int
    config: AgentCurveConfig
    gross: int
    fee: int
    net: int


TOKEN_SCALE = 10 ** TOKEN_DECIMALS


def _decode_agent_config(raw_value: bytes) -> AgentCurveConfig:
    if len(raw_value) != 40:
        raise ValueError(f"Unexpected config box length: {len(raw_value)}")
    return AgentCurveConfig(
        base_price=int.from_bytes(raw_value[0:8], "big"),
        slope=int.from_bytes(raw_value[8:16], "big"),
        buy_fee_bps=int.from_bytes(raw_value[16:24], "big"),
        sell_fee_bps=int.from_bytes(raw_value[24:32], "big"),
        graduation_threshold=int.from_bytes(raw_value[32:40], "big"),
    )


def _encode_agent_key(prefix: bytes, asset_id: int) -> bytes:
    return prefix + asset_id.to_bytes(8, "big")


def _calculate_buy_base(current_supply: int, amount: int, *, base_price: int, slope: int) -> int:
    base_cost = (amount * base_price) // TOKEN_SCALE
    area_doubled = (2 * current_supply * amount) + (amount * amount)
    slope_cost = (slope * area_doubled) // (2 * TOKEN_SCALE * TOKEN_SCALE)
    return base_cost + slope_cost


def _calculate_sell_gross(current_supply: int, amount: int, *, base_price: int, slope: int) -> int:
    new_supply = current_supply - amount
    base_return = (amount * base_price) // TOKEN_SCALE
    slope_return = (slope * ((current_supply * current_supply) - (new_supply * new_supply))) // (
        2 * TOKEN_SCALE * TOKEN_SCALE
    )
    return base_return + slope_return


async def _get_agent_state(asset_id: int) -> AgentStateResponse:
    algo = get_algorand_service()
    config_raw, supply_raw = await algo.get_application_box(
        FACTORY_APP_ID, _encode_agent_key(b"c", asset_id)
    ), await algo.get_application_box(FACTORY_APP_ID, _encode_agent_key(b"s", asset_id))
    if not config_raw:
        raise HTTPException(status_code=404, detail=f"Agent config not found for asset_id={asset_id}")

    try:
        config = _decode_agent_config(config_raw)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Corrupted agent config for asset_id={asset_id}: {exc}") from exc

    supply = int.from_bytes(supply_raw, "big") if supply_raw else 0
    return AgentStateResponse(asset_id=asset_id, supply=supply, config=config)


@router.get("/config", response_model=MarketplaceConfigResponse)
async def get_marketplace_config():
    marketplace = PROTOCOL_CONFIG.get("marketplace", {})
    next_deployment = PROTOCOL_CONFIG.get("nextDeployment", {})
    legacy_factory_ids = [
        int(entry.get("agentFactoryAppId"))
        for entry in LEGACY_DEPLOYMENTS
        if entry.get("agentFactoryAppId") is not None
    ]

    return MarketplaceConfigResponse(
        trading_enabled=bool(marketplace.get("tradingEnabled", False)),
        launch_enabled=bool(marketplace.get("launchEnabled", False)),
        maintenance_reason=marketplace.get("maintenanceReason"),
        active_factory_app_id=FACTORY_APP_ID,
        deprecated_factory_app_id=legacy_factory_ids[0] if legacy_factory_ids else FACTORY_APP_ID,
        legacy_factory_app_ids=legacy_factory_ids,
        cortex_asset_id=CORTEX_ASSET_ID,
        creation_fee=CREATION_FEE,
        buy_fee_bps=BUY_FEE_BPS,
        sell_fee_bps=SELL_FEE_BPS,
        graduation_threshold=GRADUATION_THRESHOLD,
        base_price=BASE_PRICE,
        slope=SLOPE,
        next_deployment=next_deployment,
        notes=list(marketplace.get("notes", [])),
    )


@router.get("/agents/{asset_id}/state", response_model=AgentStateResponse)
async def get_agent_state(asset_id: int):
    if asset_id <= 0:
        raise HTTPException(status_code=400, detail="asset_id must be a positive integer")
    return await _get_agent_state(asset_id)


@router.get("/quote/buy", response_model=QuotePreviewResponse)
async def preview_buy_quote(
    asset_id: int = Query(..., gt=0),
    amount: int = Query(..., gt=0),
):
    state = await _get_agent_state(asset_id)
    if amount > 100_000_000_000:
        raise HTTPException(status_code=400, detail="amount exceeds max per-transaction limit")

    gross = _calculate_buy_base(
        state.supply,
        amount,
        base_price=state.config.base_price,
        slope=state.config.slope,
    )
    fee = (gross * state.config.buy_fee_bps) // 10_000
    return QuotePreviewResponse(
        asset_id=asset_id,
        amount=amount,
        current_supply=state.supply,
        config=state.config,
        gross=gross,
        fee=fee,
        net=gross + fee,
    )


@router.get("/quote/sell", response_model=QuotePreviewResponse)
async def preview_sell_quote(
    asset_id: int = Query(..., gt=0),
    amount: int = Query(..., gt=0),
):
    state = await _get_agent_state(asset_id)
    if amount > state.supply:
        raise HTTPException(status_code=400, detail="amount exceeds current supply")
    if amount > 100_000_000_000:
        raise HTTPException(status_code=400, detail="amount exceeds max per-transaction limit")

    gross = _calculate_sell_gross(
        state.supply,
        amount,
        base_price=state.config.base_price,
        slope=state.config.slope,
    )
    fee = (gross * state.config.sell_fee_bps) // 10_000
    return QuotePreviewResponse(
        asset_id=asset_id,
        amount=amount,
        current_supply=state.supply,
        config=state.config,
        gross=gross,
        fee=fee,
        net=gross - fee,
    )

from src.api.marketplace import (
    _calculate_buy_base,
    _calculate_sell_gross,
    _decode_agent_config,
)


def _pack_u64(value: int) -> bytes:
    return value.to_bytes(8, "big")


def test_decode_agent_config_roundtrip():
    raw = (
        _pack_u64(10_000)
        + _pack_u64(1_000)
        + _pack_u64(100)
        + _pack_u64(200)
        + _pack_u64(50_000_000_000)
    )
    decoded = _decode_agent_config(raw)
    assert decoded.base_price == 10_000
    assert decoded.slope == 1_000
    assert decoded.buy_fee_bps == 100
    assert decoded.sell_fee_bps == 200
    assert decoded.graduation_threshold == 50_000_000_000


def test_buy_and_sell_quote_math_matches_scaled_curve():
    current_supply = 5_000_000
    amount = 1_000_000
    base_price = 10_000
    slope = 1_000

    gross_buy = _calculate_buy_base(
        current_supply,
        amount,
        base_price=base_price,
        slope=slope,
    )
    assert gross_buy > 0

    gross_sell = _calculate_sell_gross(
        current_supply,
        amount,
        base_price=base_price,
        slope=slope,
    )
    assert gross_sell > 0
    assert gross_buy > gross_sell

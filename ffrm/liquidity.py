"""
LAYER 5 (part B) — LIQUIDITY.

A NAV mark is only worth what you can actually sell it for, in time. So we:
  1) haircut less-liquid assets more (feeds the borrowing base in Layer 1), and
  2) check whether enough of the portfolio can be sold within a horizon to cover
     the loan (a liquidity-coverage view, separate from LTV).

Engineering analogy: a slow, hard-to-read sensor gets a bigger noise margin.
"""


def liquidity_factor(asset) -> float:
    """Multiplier in (0,1]; the faster an asset can be sold, the closer to 1."""
    d = asset.liquidity_days
    if d <= 30:
        return 1.00
    if d <= 90:
        return 0.90
    if d <= 180:
        return 0.75
    return 0.60


def liquid_value(fund, horizon_days: float = 90) -> float:
    """Total NAV that can be liquidated within the horizon."""
    return sum(a.nav for a in fund.assets if a.liquidity_days <= horizon_days)


def liquidity_coverage(fund, facility, horizon_days: float = 90) -> float:
    """
    Liquidity-coverage ratio = liquidatable value within horizon / amount drawn.
    >= 1 means we could repay the loan by selling liquid assets in time.
    """
    if facility.drawn <= 0:
        return float("inf")
    return liquid_value(fund, horizon_days) / facility.drawn

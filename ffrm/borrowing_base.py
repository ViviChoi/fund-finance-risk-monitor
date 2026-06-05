"""
LAYER 1 — BORROWING BASE, EXPOSURE & HEALTH FACTOR.

Upgrades vs v1:
  * Sub-line collateral is EL-weighted (Layer 2) -- no binary cliff.
  * NAV collateral is haircut per asset by liquidity (Layer 5).
  * Adds Health Factor: an Aave/Compound-style single risk number that
    is the fund-finance equivalent of a control-system stability margin.

Vocabulary: borrowing base, advance rate / LTV, eligibility weight,
concentration cap, availability (headroom), utilization, health factor.
"""

from ffrm.credit_scoring import eligibility_weight, is_eligible
from ffrm.liquidity import liquidity_factor

LP_CONCENTRATION_CAP = 0.25       # no single LP > 25% of the eligible pool
LIQ_THRESHOLD = 0.85              # safe slice of the borrowing base for HF


def subscription_borrowing_base(fund, facility) -> float:
    """
    EL-weighted sub-line. Each LP's uncalled is multiplied by their
    continuous eligibility weight, then a concentration cap, then the
    facility's advance rate.
    """
    weighted = [lp.uncalled * eligibility_weight(lp) for lp in fund.lps]
    total = sum(weighted)
    if total == 0:
        return 0.0
    cap = LP_CONCENTRATION_CAP * total
    capped = sum(min(v, cap) for v in weighted)
    return facility.advance_rate * capped


def nav_borrowing_base(fund, facility) -> float:
    """advance_rate * sum of each asset's NAV after its liquidity haircut."""
    return facility.advance_rate * sum(a.nav * liquidity_factor(a) for a in fund.assets)


def borrowing_base(fund, facility) -> float:
    if facility.kind == "subscription":
        return subscription_borrowing_base(fund, facility)
    if facility.kind == "nav":
        return nav_borrowing_base(fund, facility)
    raise ValueError(f"Unknown facility kind: {facility.kind!r}")


def effective_limit(fund, facility) -> float:
    return min(borrowing_base(fund, facility), facility.limit)


def availability(fund, facility) -> float:
    return effective_limit(fund, facility) - facility.drawn


def utilization(fund, facility) -> float:
    lim = effective_limit(fund, facility)
    return facility.drawn / lim if lim > 0 else float("inf")


def ltv(fund, facility) -> float:
    return facility.drawn / fund.total_nav if fund.total_nav > 0 else float("inf")


def health_factor(fund, facility, liq_thresh: float = LIQ_THRESHOLD) -> float:
    """
    Aave/Compound-style single risk number.

        HF = (effective_limit * liq_thresh) / drawn

    HF > 1   -> safe;
    HF = 1   -> at the liquidation threshold;
    HF < 1   -> margin call.

    Engineering analogy: stability margin in a multi-loop control system --
    one normalised number that tells you how far from instability you are.
    """
    if facility.drawn <= 0:
        return float("inf")
    safe_capacity = effective_limit(fund, facility) * liq_thresh
    return safe_capacity / facility.drawn

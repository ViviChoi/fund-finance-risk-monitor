"""
LAYER 4 (part A) — COVENANTS as a traffic light.

Each covenant returns GREEN / AMBER / RED:
  GREEN  = comfortable
  AMBER  = inside an early-warning band (approaching the limit)
  RED    = breached

New vs v1:
  * Adds a Health Factor covenant (a single Aave-style risk number).
  * All `check_*` functions now take (fund, facility) uniformly, so the
    reverse-stress engine can iterate over them with one signature.

Engineering analogy: a protective relay does not only trip -- it has an
alarm band before the trip threshold. AMBER is that alarm band.
"""

from dataclasses import dataclass

from ffrm.borrowing_base import (
    availability, effective_limit, utilization, ltv, health_factor,
)
from ffrm.liquidity import liquidity_coverage

GREEN, AMBER, RED = "GREEN", "AMBER", "RED"

# thresholds (illustrative; negotiated per deal in reality)
MAX_LTV = 0.25
MAX_ASSET_CONC = 0.35
MAX_SECTOR_CONC = 0.40
MIN_ASSETS = 4
UTIL_WARN = 0.85          # amber if utilization >= 85%
WARN_FRACTION = 0.90      # amber if within 90% of a "higher-is-worse" limit
MIN_LIQ_COVER = 1.0       # need >=1.0x; amber below 2.0x
HF_RED = 1.0              # health factor < 1.0 -> liquidation
HF_AMBER = 1.5            # health factor < 1.5 -> early warning


@dataclass
class CovenantResult:
    name: str
    actual: float
    limit: float
    status: str
    note: str = ""


def _hi_worse(name, actual, limit, warn_fraction=WARN_FRACTION, note=""):
    """Status for ratios where higher = worse (LTV, concentration)."""
    if actual > limit:
        status = RED
    elif actual >= warn_fraction * limit:
        status = AMBER
    else:
        status = GREEN
    return CovenantResult(name, actual, limit, status, note)


def check_max_ltv(fund, facility):
    return _hi_worse("Max LTV", ltv(fund, facility), MAX_LTV, note="loan / NAV")


def check_asset_concentration(fund, facility=None):
    if fund.total_nav == 0:
        return CovenantResult("Single-asset concentration", float("inf"), MAX_ASSET_CONC, RED)
    largest = max(a.nav for a in fund.assets) / fund.total_nav
    return _hi_worse("Single-asset concentration", largest, MAX_ASSET_CONC, note="largest asset / NAV")


def check_sector_concentration(fund, facility=None):
    if fund.total_nav == 0:
        return CovenantResult("Sector concentration", float("inf"), MAX_SECTOR_CONC, RED)
    sectors = {}
    for a in fund.assets:
        sectors[a.sector] = sectors.get(a.sector, 0.0) + a.nav
    largest = max(sectors.values()) / fund.total_nav
    return _hi_worse("Sector concentration", largest, MAX_SECTOR_CONC, note="largest sector / NAV")


def check_utilization(fund, facility):
    u = utilization(fund, facility)
    status = RED if u > 1.0 else (AMBER if u >= UTIL_WARN else GREEN)
    return CovenantResult("Utilization", u, 1.0, status, note="drawn / effective limit")


def check_borrowing_base(fund, facility):
    avail = availability(fund, facility)
    lim = effective_limit(fund, facility)
    if avail < 0:
        status = RED
    elif lim > 0 and avail < (1 - UTIL_WARN) * lim:
        status = AMBER
    else:
        status = GREEN
    return CovenantResult("Borrowing-base headroom", avail, 0.0, status, note="availability >= 0")


def check_health_factor(fund, facility):
    hf = health_factor(fund, facility)
    if hf < HF_RED:
        status = RED
    elif hf < HF_AMBER:
        status = AMBER
    else:
        status = GREEN
    return CovenantResult("Health Factor", hf, HF_RED, status,
                          note="(eff_limit x liq_thresh) / drawn")


def check_diversification(fund, facility=None):
    n = len(fund.assets)
    status = GREEN if n >= MIN_ASSETS else RED
    return CovenantResult("Min number of assets", n, MIN_ASSETS, status, note="count")


def check_liquidity(fund, facility, horizon_days=90):
    cov = liquidity_coverage(fund, facility, horizon_days)
    status = RED if cov < MIN_LIQ_COVER else (AMBER if cov < 2.0 else GREEN)
    return CovenantResult("Liquidity coverage", cov, MIN_LIQ_COVER, status,
                          note=f"liquid value <= {horizon_days}d / drawn")


def run_all(fund, facility):
    return [
        check_borrowing_base(fund, facility),
        check_health_factor(fund, facility),
        check_utilization(fund, facility),
        check_max_ltv(fund, facility),
        check_asset_concentration(fund, facility),
        check_sector_concentration(fund, facility),
        check_liquidity(fund, facility),
        check_diversification(fund, facility),
    ]

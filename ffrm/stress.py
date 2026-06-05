"""
LAYER 3 — STRESS & SCENARIO ANALYSIS.

Three views, each answering a different question:
  (a) Deterministic NAV haircut sweep   -> a transient view of a single
      breaking point (the engineering 'worst-case fault test').
  (b) Reverse stress per covenant       -> distance-to-breach ranked across
      every covenant. The fund-finance equivalent of a per-loop stability
      margin: you do not just look at the main loop, you rank all loops.
  (c) Multi-factor Monte Carlo          -> sector-correlated lognormal NAV
      shocks, returning P(breach), VaR(95), CVaR(99) and a per-sector
      attribution of which factor is driving breaches. The fund-finance
      analogue of cross-PSD noise analysis under coupled disturbances.

Uses numpy when available for vectorised MC (~100-1000x speedup);
falls back transparently to a single-shock stdlib model otherwise.
"""

import copy
import math
import random

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from ffrm.borrowing_base import borrowing_base, availability, ltv
from ffrm.covenants import (
    MAX_LTV, RED,
    check_borrowing_base, check_health_factor, check_utilization,
    check_max_ltv, check_asset_concentration, check_sector_concentration,
    check_liquidity, check_diversification,
)


# ----------------------------------------------------------------------------
# Sector-factor parameters (approx. MSCI Barra US Total Market Equity Model)
# Annualised volatilities + cross-sector correlation matrix.
# ----------------------------------------------------------------------------
SECTOR_VOL = {
    "Technology":   0.30,
    "Healthcare":   0.20,
    "Industrials":  0.22,
    "Consumer":     0.18,
    "Financials":   0.25,
    "Energy":       0.28,
    "Materials":    0.24,
    "Real Estate":  0.22,
    "Utilities":    0.15,
    "Other":        0.20,
}

SECTOR_ORDER = [
    "Technology", "Healthcare", "Industrials", "Consumer", "Financials",
    "Energy", "Materials", "Real Estate", "Utilities", "Other",
]

# Cross-sector correlation matrix (symmetric, 1.0 on the diagonal)
_CORR = [
    # Tech  Hlth  Ind   Cons  Fin   Eng   Mat   RE    Util  Other
    [1.00, 0.40, 0.55, 0.45, 0.55, 0.35, 0.45, 0.40, 0.30, 0.40],
    [0.40, 1.00, 0.30, 0.35, 0.30, 0.20, 0.25, 0.30, 0.25, 0.30],
    [0.55, 0.30, 1.00, 0.55, 0.60, 0.55, 0.65, 0.50, 0.45, 0.50],
    [0.45, 0.35, 0.55, 1.00, 0.50, 0.35, 0.45, 0.50, 0.40, 0.45],
    [0.55, 0.30, 0.60, 0.50, 1.00, 0.45, 0.50, 0.65, 0.40, 0.50],
    [0.35, 0.20, 0.55, 0.35, 0.45, 1.00, 0.55, 0.40, 0.40, 0.35],
    [0.45, 0.25, 0.65, 0.45, 0.50, 0.55, 1.00, 0.45, 0.40, 0.40],
    [0.40, 0.30, 0.50, 0.50, 0.65, 0.40, 0.45, 1.00, 0.50, 0.45],
    [0.30, 0.25, 0.45, 0.40, 0.40, 0.40, 0.40, 0.50, 1.00, 0.35],
    [0.40, 0.30, 0.50, 0.45, 0.50, 0.35, 0.40, 0.45, 0.35, 1.00],
]


# ----------------------------------------------------------------------------
# Deterministic stress (kept from v1)
# ----------------------------------------------------------------------------
def apply_nav_haircut(fund, haircut: float):
    s = copy.deepcopy(fund)
    for a in s.assets:
        a.nav *= (1.0 - haircut)
    return s


def drop_lp(fund, lp_name: str):
    s = copy.deepcopy(fund)
    s.lps = [lp for lp in s.lps if lp.name != lp_name]
    return s


def stress_nav(fund, facility, haircuts, max_ltv: float = MAX_LTV):
    rows = []
    for h in haircuts:
        s = apply_nav_haircut(fund, h)
        rows.append({
            "haircut": h,
            "total_nav": s.total_nav,
            "borrowing_base": borrowing_base(s, facility),
            "availability": availability(s, facility),
            "ltv": ltv(s, facility),
            "ltv_breach": ltv(s, facility) > max_ltv,
            "bb_deficiency": availability(s, facility) < 0,
        })
    return rows


def first_breach_haircut(fund, facility, step=0.005, max_haircut=0.90, max_ltv=MAX_LTV):
    h = 0.0
    while h <= max_haircut:
        s = apply_nav_haircut(fund, h)
        if availability(s, facility) < 0:
            return round(h, 4), "borrowing-base deficiency (drawn > borrowing base)"
        if ltv(s, facility) > max_ltv:
            return round(h, 4), "max-LTV covenant breach"
        h += step
    return None, None


# ----------------------------------------------------------------------------
# Reverse stress per covenant (Change 4)
# ----------------------------------------------------------------------------
def _breaking_point(fund, facility, covenant_check, max_h=0.90, tol=0.001):
    """Bisection: smallest NAV haircut at which this covenant turns RED."""
    if covenant_check(fund, facility).status == RED:
        return 0.0
    if covenant_check(apply_nav_haircut(fund, max_h), facility).status != RED:
        return None
    lo, hi = 0.0, max_h
    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        if covenant_check(apply_nav_haircut(fund, mid), facility).status == RED:
            hi = mid
        else:
            lo = mid
    return round(hi, 4)


def reverse_stress_ranking(fund, facility):
    """
    For every covenant, find the NAV haircut at which it first turns RED.
    Returns a list sorted by ascending breaking-haircut (closest binding
    constraint first; covenants that never break are placed last).
    """
    covenants = [
        ("Borrowing-base headroom",   check_borrowing_base),
        ("Health Factor",             check_health_factor),
        ("Utilization",               check_utilization),
        ("Max LTV",                   check_max_ltv),
        ("Asset concentration",       check_asset_concentration),
        ("Sector concentration",      check_sector_concentration),
        ("Liquidity coverage",        check_liquidity),
        ("Min number of assets",      check_diversification),
    ]
    results = []
    for name, check in covenants:
        h = _breaking_point(fund, facility, check)
        results.append({"covenant": name, "breaking_haircut": h})

    results.sort(key=lambda x: (
        x["breaking_haircut"] is None,
        x["breaking_haircut"] if x["breaking_haircut"] is not None else 1.0,
    ))
    for i, r in enumerate(results):
        r["rank"] = i + 1 if r["breaking_haircut"] is not None else None
    return results


# ----------------------------------------------------------------------------
# Multi-factor Monte Carlo (Change 3)
# ----------------------------------------------------------------------------
def _covariance_matrix(horizon_years: float):
    """Sigma_ij = rho_ij * sigma_i * sigma_j * sqrt(horizon)^2."""
    n = len(SECTOR_ORDER)
    sigmas = [SECTOR_VOL[s] * math.sqrt(horizon_years) for s in SECTOR_ORDER]
    cov = [[_CORR[i][j] * sigmas[i] * sigmas[j] for j in range(n)] for i in range(n)]
    return cov, sigmas


def monte_carlo(fund, facility, n_sims=20000, horizon=0.5,
                max_ltv=MAX_LTV, seed=42):
    """
    Multi-factor Monte Carlo. Each sector is a risk factor with its own
    annualised vol; cross-sector correlations come from SECTOR_CORR.
    Returns P(breach), VaR(95), CVaR(99) and per-sector attribution.

    Engineering view: this is cross-PSD noise analysis -- per-source
    variance plus an off-diagonal coupling matrix -- propagated through
    the (linear) NAV summation to the (non-linear) LTV ratio.
    """
    if not HAS_NUMPY:
        return _monte_carlo_fallback(fund, facility, n_sims, horizon, max_ltv, seed)

    cov, _ = _covariance_matrix(horizon)
    cov = np.array(cov)
    rng = np.random.default_rng(seed)

    z = rng.multivariate_normal(np.zeros(len(SECTOR_ORDER)), cov, size=n_sims)
    shocks = np.exp(z)                                   # multivariate lognormal

    idx = {s: i for i, s in enumerate(SECTOR_ORDER)}
    base_navs = np.array([a.nav for a in fund.assets], dtype=float)
    asset_sec = np.array([idx.get(a.sector, idx["Other"]) for a in fund.assets])

    shocked = base_navs[None, :] * shocks[:, asset_sec]   # (n_sims, n_assets)
    total_navs = shocked.sum(axis=1)
    ltvs = np.where(total_navs > 0, facility.drawn / total_navs, np.inf)

    breach_mask = ltvs > max_ltv
    finite = ltvs[np.isfinite(ltvs)]
    finite_sorted = np.sort(finite)
    n_finite = len(finite_sorted)

    def _pct(p):
        if n_finite == 0:
            return float("inf")
        return float(finite_sorted[min(n_finite - 1, int(p * n_finite))])

    var95 = _pct(0.95)
    var99_idx = int(0.99 * n_finite) if n_finite else 0
    cvar99 = (float(finite_sorted[var99_idx:].mean())
              if n_finite > var99_idx else float("inf"))

    # Sector attribution: average drawdown of each sector conditional on a breach.
    attribution = {}
    if breach_mask.any():
        for s, i in idx.items():
            attribution[s] = float(1.0 - shocks[breach_mask, i].mean())

    return {
        "n_sims": n_sims,
        "horizon_years": horizon,
        "p_ltv_breach": float(breach_mask.mean()),
        "var95_ltv": var95,
        "cvar99_ltv": cvar99,
        "ltv_p50": _pct(0.50),
        "ltv_p95": var95,
        "ltv_p99": _pct(0.99),
        "sector_attribution": attribution,
        "model": "multi-factor lognormal (numpy vectorised)",
    }


def _monte_carlo_fallback(fund, facility, n_sims, horizon, max_ltv, seed):
    """Single-shock fallback for environments without numpy."""
    rng = random.Random(seed)
    sigma = 0.20 * math.sqrt(horizon)
    breach = 0
    ltvs = []
    for _ in range(n_sims):
        shock = math.exp(rng.gauss(0.0, sigma))
        total_nav = sum(a.nav for a in fund.assets) * shock
        cur_ltv = facility.drawn / total_nav if total_nav > 0 else float("inf")
        ltvs.append(cur_ltv)
        if cur_ltv > max_ltv:
            breach += 1
    ltvs.sort()

    def pct(p):
        return ltvs[min(len(ltvs) - 1, int(p * len(ltvs)))]

    var99_idx = int(0.99 * len(ltvs))
    cvar99 = (sum(ltvs[var99_idx:]) / max(1, len(ltvs) - var99_idx)
              if ltvs else float("inf"))
    return {
        "n_sims": n_sims,
        "horizon_years": horizon,
        "p_ltv_breach": breach / n_sims if n_sims else 0.0,
        "var95_ltv": pct(0.95),
        "cvar99_ltv": cvar99,
        "ltv_p50": pct(0.50),
        "ltv_p95": pct(0.95),
        "ltv_p99": pct(0.99),
        "sector_attribution": {},
        "model": "single-shock fallback (numpy not installed)",
    }

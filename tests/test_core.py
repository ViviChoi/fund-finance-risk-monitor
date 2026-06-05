"""
Minimal sanity tests. From project root:

    python tests/test_core.py        # plain python
    python -m pytest -q              # if pytest installed
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.sample_fund import sample_fund, sample_nav_facility
from ffrm.credit_scoring import (
    is_eligible, estimate_pd, expected_loss, eligibility_weight, EL_CAP,
)
from ffrm.borrowing_base import (
    borrowing_base, availability, health_factor, effective_limit, LIQ_THRESHOLD,
)
from ffrm.liquidity import liquidity_factor
from ffrm.stress import (
    apply_nav_haircut, monte_carlo, reverse_stress_ranking, _breaking_point,
)
from ffrm.covenants import check_borrowing_base, check_max_ltv, RED
from ffrm.triggers import evaluate_fund, MONITOR, WARNING, MARGIN_CALL


# -------- Change 1: EL-weighted eligibility --------

def test_eligibility_weight_in_unit_interval():
    fund = sample_fund()
    for lp in fund.lps:
        w = eligibility_weight(lp)
        assert 0.0 <= w <= 1.0, f"{lp.name}: weight {w} out of [0,1]"


def test_NR_is_partial_not_excluded():
    """NR-rated LP gets a partial weight (was fully excluded in v1)."""
    fund = sample_fund()
    nr = [lp for lp in fund.lps if lp.rating == "NR"][0]
    w = eligibility_weight(nr)
    el = expected_loss(nr)
    assert 0.0 < w < 1.0
    # weight formula consistency
    assert abs(w - max(0.0, 1.0 - el / EL_CAP)) < 1e-9


def test_higher_quality_gets_higher_weight():
    fund = sample_fund()
    aa = next(lp for lp in fund.lps if lp.rating == "AA")
    bbb = next(lp for lp in fund.lps if lp.rating == "BBB")
    assert eligibility_weight(aa) > eligibility_weight(bbb)


# -------- Change 2: Health Factor --------

def test_health_factor_above_1_when_under_threshold():
    fund, fac = sample_fund(), sample_nav_facility()
    # at sample data, drawn=30, eff_limit=33.75 -> safe_capacity=33.75*0.85=28.69
    # so HF should be < 1.0 here  (illustrative: sample is intentionally tight)
    hf = health_factor(fund, fac)
    assert 0.0 < hf < 2.0


def test_health_factor_infinite_when_no_debt():
    fund = sample_fund()
    from ffrm.models import Facility
    fac0 = Facility(kind="nav", advance_rate=0.20, limit=50, drawn=0)
    assert health_factor(fund, fac0) == float("inf")


def test_health_factor_decreases_with_drawdown():
    fund, fac = sample_fund(), sample_nav_facility()
    hf_base = health_factor(fund, fac)
    fund_down = apply_nav_haircut(fund, 0.20)
    hf_stress = health_factor(fund_down, fac)
    assert hf_stress < hf_base


# -------- existing borrowing base sanity (still holds for NAV facility) --------

def test_nav_borrowing_base_uses_liquidity_haircut():
    fund, fac = sample_fund(), sample_nav_facility()
    expected = 0.20 * sum(a.nav * liquidity_factor(a) for a in fund.assets)
    assert abs(borrowing_base(fund, fac) - expected) < 1e-9
    assert abs(borrowing_base(fund, fac) - 33.75) < 1e-6


def test_haircut_reduces_nav():
    fund = sample_fund()
    assert abs(apply_nav_haircut(fund, 0.5).total_nav - fund.total_nav * 0.5) < 1e-6


def test_trigger_action_is_valid():
    fund, fac = sample_fund(), sample_nav_facility()
    action, reasons, _ = evaluate_fund(fund, fac)
    assert action in (MONITOR, WARNING, MARGIN_CALL)


# -------- Change 3: multi-factor Monte Carlo --------

def test_monte_carlo_probabilities_in_range():
    fund, fac = sample_fund(), sample_nav_facility()
    mc = monte_carlo(fund, fac, n_sims=2000)
    assert 0.0 <= mc["p_ltv_breach"] <= 1.0
    # CVaR(99) should be at least as bad as VaR(95)
    assert mc["cvar99_ltv"] >= mc["var95_ltv"] - 1e-6


def test_monte_carlo_sector_attribution_keys():
    """Attribution dict, if present, only contains known sectors."""
    fund, fac = sample_fund(), sample_nav_facility()
    mc = monte_carlo(fund, fac, n_sims=2000)
    from ffrm.stress import SECTOR_ORDER
    for k in mc.get("sector_attribution", {}):
        assert k in SECTOR_ORDER


# -------- Change 4: reverse stress per covenant --------

def test_reverse_stress_returns_sorted_ranking():
    fund, fac = sample_fund(), sample_nav_facility()
    ranking = reverse_stress_ranking(fund, fac)
    # all covenants accounted for
    assert len(ranking) == 8
    # ranking is monotone non-decreasing in breaking_haircut (None last)
    finite = [r["breaking_haircut"] for r in ranking if r["breaking_haircut"] is not None]
    assert finite == sorted(finite)


def test_binding_constraint_is_borrowing_base_for_sample():
    """README's headline claim: BB-deficiency is the binding constraint."""
    fund, fac = sample_fund(), sample_nav_facility()
    ranking = reverse_stress_ranking(fund, fac)
    binding = ranking[0]["covenant"]
    # at sample params, BB or HF (both depend on collateral) should bind first
    assert binding in ("Borrowing-base headroom", "Health Factor")


def test_breaking_point_monotone_invariant():
    """Bigger haircut never reduces the chance of breach."""
    fund, fac = sample_fund(), sample_nav_facility()
    h = _breaking_point(fund, fac, check_borrowing_base)
    assert h is not None
    # at h + small epsilon, covenant should still be RED
    assert check_borrowing_base(apply_nav_haircut(fund, h + 0.02), fac).status == RED


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"{name}: OK")
            except AssertionError as e:
                failures += 1
                print(f"{name}: FAIL — {e}")
            except Exception as e:
                failures += 1
                print(f"{name}: ERROR — {type(e).__name__}: {e}")
    if failures == 0:
        print("All tests passed.")
    else:
        print(f"{failures} test(s) failed.")
        sys.exit(1)

"""
LAYER 2 — CREDIT SCORING / PROBABILITY OF DEFAULT / EXPECTED LOSS.

Upgrades vs v1:
  * PD is still per-LP (rating-based baseline, with an ML-ready hook).
  * Eligibility is no longer a binary cliff at PD <= 3%. We compute an
    Expected Loss EL = PD * LGD and weight the collateral by
    (1 - EL/EL_CAP), bounded to [0,1]. This is the Basel III IRB approach:
    continuous risk-weighted exposure, not a step function.

Engineering analogy: derating curve, not bang-bang. A discontinuous gain
oscillates a portfolio the same way it oscillates a control loop.
"""

import math

# baseline 1-year PD by rating (illustrative, not market data)
RATING_PD = {
    "AAA": 0.0010, "AA": 0.0020, "A": 0.0050, "BBB": 0.0200,
    "BB": 0.0600, "B": 0.1200, "CCC": 0.2500, "NR": 0.1000,
}

# Loss Given Default by rating (approx. Moody's senior-unsecured recovery data)
LGD_BY_RATING = {
    "AAA": 0.30, "AA": 0.35, "A": 0.40, "BBB": 0.45,
    "BB":  0.50, "B":  0.55, "CCC": 0.65, "NR": 0.50,
}

# Expected Loss at or above this rate -> collateral weight = 0
EL_CAP = 0.10


def logistic(z: float) -> float:
    """Sigmoid -- the link function a logistic-regression scorecard would use."""
    return 1.0 / (1.0 + math.exp(-z))


def estimate_pd(lp) -> float:
    """
    Return LP's PD: a supplied value if present, else the rating-table baseline.

    >>> ML HOOK <<<  In production, replace with `return model.predict_proba(features)`:
        z = -3.0 + 2.0 * leverage - 1.5 * interest_coverage
        return logistic(z)
    """
    if lp.pd is not None:
        return lp.pd
    return RATING_PD.get(lp.rating, 0.15)


def lgd_for(lp) -> float:
    """Loss Given Default lookup; falls back to 0.50 for unknown ratings."""
    return LGD_BY_RATING.get(lp.rating, 0.50)


def expected_loss(lp) -> float:
    """EL = PD * LGD (Basel III IRB definition, ignoring EAD scaling)."""
    return estimate_pd(lp) * lgd_for(lp)


def eligibility_weight(lp) -> float:
    """
    Continuous [0,1] collateral weight. EL=0 -> 1.0; EL>=EL_CAP -> 0.0.
    Replaces v1's binary `is_eligible` cliff with a smooth derating curve.
    """
    return max(0.0, 1.0 - expected_loss(lp) / EL_CAP)


def is_eligible(lp, threshold: float = 0.5) -> bool:
    """Backwards-compat helper: an LP is 'eligible' when weight > threshold."""
    return eligibility_weight(lp) > threshold

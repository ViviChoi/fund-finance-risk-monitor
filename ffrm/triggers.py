"""
LAYER 4 (part B) — TRIGGER ENGINE (a small state machine).

Covenant colours -> lender ACTION with a time-graded cure period:

    all GREEN            -> MONITOR
    any AMBER            -> WARNING        (watch closely, talk to sponsor)
    any RED              -> MARGIN_CALL    (post collateral / repay)
    RED beyond cure_days -> EVENT_OF_DEFAULT

New vs v1: the cure window itself shrinks as the Health Factor falls --
the deeper into margin-call territory you go, the less time to fix it.
Same principle as time-graded protective-relay coordination: a fault
deeper into the protected zone trips faster.
"""

from ffrm.covenants import GREEN, AMBER, RED, run_all
from ffrm.borrowing_base import health_factor

MONITOR = "MONITOR"
WARNING = "WARNING"
MARGIN_CALL = "MARGIN_CALL"
EVENT_OF_DEFAULT = "EVENT_OF_DEFAULT"


def cure_days_for(hf: float, base: int = 10) -> int:
    """HF-aware cure period: deeper distress = shorter window."""
    if hf >= 1.0:
        return base                  # full negotiated window
    if hf >= 0.8:
        return max(1, base // 2)     # half the window
    return 0                         # severe -- immediate trip


def evaluate(results, days_in_breach: int = 0, cure_days: int = 10):
    """Return (action, reasons) given covenant results and how long RED has persisted."""
    reds = [r.name for r in results if r.status == RED]
    ambers = [r.name for r in results if r.status == AMBER]

    if reds:
        action = EVENT_OF_DEFAULT if days_in_breach > cure_days else MARGIN_CALL
        return action, reds
    if ambers:
        return WARNING, ambers
    return MONITOR, []


def evaluate_fund(fund, facility, days_in_breach: int = 0):
    """Run covenants, fold in HF-aware cure window, then the trigger engine."""
    results = run_all(fund, facility)
    hf = health_factor(fund, facility)
    cure = cure_days_for(hf, facility.cure_days)
    action, reasons = evaluate(results, days_in_breach, cure)
    return action, reasons, results

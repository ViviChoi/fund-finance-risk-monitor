"""
Entry point — runs the whole 6-layer pipeline on synthetic data:

    python scripts/run_monitor.py

Pipeline (matches the architecture diagram):
  Layer 5 ingest/validate -> Layer 2 credit/EL -> Layer 1 borrowing base
  -> Layer 5 liquidity -> Layer 4 covenants+triggers
  -> Layer 3 deterministic stress + reverse stress + multi-factor MC -> output
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.sample_fund import sample_fund, sample_nav_facility, sample_subscription_facility
from ffrm import report
from ffrm.data_ingest import validate
from ffrm.stress import (
    stress_nav, first_breach_haircut, monte_carlo, reverse_stress_ranking,
)
from ffrm.covenants import MAX_LTV
from ffrm.triggers import evaluate_fund


def run(fund, facility, title):
    print("\n" + "#" * 72)
    print(f"### {title}")
    print("#" * 72)
    action, reasons, _ = evaluate_fund(fund, facility)
    report.print_summary(fund, facility, action=action, reasons=reasons)


def main():
    # ---- Layer 5: ingest + validate ----
    fund = sample_fund()
    snap = validate(fund, source="synthetic")
    report.print_data_snapshot(snap)

    # ---- Layer 2: credit / EL-weighted eligibility ----
    report.print_credit(fund)

    # ---- NAV facility: full monitor ----
    nav_fac = sample_nav_facility()
    run(fund, nav_fac, "NAV FACILITY")

    # ---- Layer 3: deterministic + reverse + multi-factor MC ----
    rows = stress_nav(fund, nav_fac, [i / 100 for i in range(0, 55, 5)], max_ltv=MAX_LTV)
    report.print_stress_table(rows)
    h, why = first_breach_haircut(fund, nav_fac, max_ltv=MAX_LTV)
    if h is not None:
        print(f"\n[Layer 3] First breach at NAV drop ~{h:.1%} -> {why}.")
    else:
        print("\n[Layer 3] No breach within tested range.")

    ranking = reverse_stress_ranking(fund, nav_fac)
    report.print_reverse_stress(ranking)

    mc = monte_carlo(fund, nav_fac, n_sims=20000, horizon=0.5)
    report.print_monte_carlo(mc)

    import os
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    FIG = os.path.join(ROOT, "figures")
    os.makedirs(FIG, exist_ok=True)
    report.save_stress_chart(rows, MAX_LTV, path=os.path.join(FIG, "stress_chart.png"))
    report.save_reverse_stress_chart(ranking, path=os.path.join(FIG, "reverse_stress.png"))

    # ---- Subscription line: monitor only (EL-weighted sub-line collateral) ----
    run(fund, sample_subscription_facility(), "SUBSCRIPTION LINE")


if __name__ == "__main__":
    main()

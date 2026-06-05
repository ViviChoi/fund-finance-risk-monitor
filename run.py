"""
Fund Finance Facility Risk Monitor — easy launcher.

Run this from anywhere:

    Windows :  python run.py
    Mac     :  python3 run.py

It reads the three CSV files in the sample_data/ folder (open them in Excel
or Numbers to change the numbers), runs all six layers, prints the full
report, and saves two stress charts (stress_chart.png + reverse_stress.png)
if matplotlib is installed.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ffrm import report
from ffrm.data_ingest import validate
from ffrm.stress import (
    stress_nav, first_breach_haircut, monte_carlo, reverse_stress_ranking,
)
from ffrm.covenants import MAX_LTV
from ffrm.triggers import evaluate_fund
from ffrm.load_csv import load_fund, load_facility

DATA = os.path.join(HERE, "sample_data")
FIGURES = os.path.join(HERE, "figures")
os.makedirs(FIGURES, exist_ok=True)


def main():
    # ---- Layer 5: load + validate the CSV inputs ----
    fund = load_fund(DATA, name="Project Alpha Fund")
    facility = load_facility(DATA)
    snap = validate(fund, source="sample_data/*.csv")
    report.print_data_snapshot(snap)
    if not snap.ok:
        print("  -> please fix the data warnings above and run again.")

    # ---- Layer 2: credit / EL-weighted eligibility (Basel III IRB-style) ----
    report.print_credit(fund)

    # ---- Layers 1, 4, 5: size the loan, check limits, decide an action ----
    action, reasons, _ = evaluate_fund(fund, facility)
    report.print_summary(fund, facility, action=action, reasons=reasons)

    # ---- Layer 3a: deterministic NAV sweep ----
    rows = stress_nav(fund, facility, [i / 100 for i in range(0, 55, 5)], max_ltv=MAX_LTV)
    report.print_stress_table(rows)
    h, why = first_breach_haircut(fund, facility, max_ltv=MAX_LTV)
    if h is not None:
        print(f"\n[Layer 3] First breach at NAV drop ~{h:.0%} -> {why}.")
    else:
        print("\n[Layer 3] No breach within the tested range.")

    # ---- Layer 3b: reverse stress per covenant (distance-to-breach ranking) ----
    ranking = reverse_stress_ranking(fund, facility)
    report.print_reverse_stress(ranking)

    # ---- Layer 3c: multi-factor Monte Carlo with sector correlations ----
    mc = monte_carlo(fund, facility, n_sims=20000, horizon=0.5)
    report.print_monte_carlo(mc)

    # ---- charts (optional, matplotlib only) ----
    report.save_stress_chart(rows, MAX_LTV, path=os.path.join(FIGURES, "stress_chart.png"))
    report.save_reverse_stress_chart(ranking, path=os.path.join(FIGURES, "reverse_stress.png"))

    print("\nDone. Edit the CSVs in sample_data/ and run again to try other scenarios.")


if __name__ == "__main__":
    main()

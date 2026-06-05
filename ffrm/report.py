"""
OUTPUT LAYER — console report + optional charts.
matplotlib is optional; the text report always works.
"""

from ffrm.borrowing_base import (
    borrowing_base, effective_limit, availability, utilization, ltv,
    health_factor,
)
from ffrm import covenants
from ffrm.credit_scoring import (
    estimate_pd, lgd_for, expected_loss, eligibility_weight,
)
from ffrm.liquidity import liquidity_coverage

DOT = {"GREEN": "[GREEN]", "AMBER": "[AMBER]", "RED": "[ RED ]"}


def _f(x):
    return f"{x:,.2f}"


def print_data_snapshot(snap):
    print(f"[Layer 5] Data snapshot @ {snap.timestamp}  source={snap.source}  "
          f"LPs={snap.n_lps} assets={snap.n_assets}  "
          f"quality={'OK' if snap.ok else 'WARNINGS: ' + '; '.join(snap.warnings)}")


def print_credit(fund):
    print("[Layer 2] LP credit / EL-weighted eligibility (Basel III IRB-style):")
    print(f"    {'LP':<18} {'rating':<6} {'PD':>6}  {'LGD':>6}  {'EL':>6}  {'weight':>8}")
    for lp in fund.lps:
        w = eligibility_weight(lp)
        tag = "eligible" if w > 0.5 else ("partial" if w > 0 else "EXCLUDED")
        print(f"    {lp.name:<18} {lp.rating:<6} "
              f"{estimate_pd(lp):>6.2%}  {lgd_for(lp):>6.0%}  "
              f"{expected_loss(lp):>6.2%}  {w:>7.2f}  -> {tag}")


def print_summary(fund, facility, action=None, reasons=None):
    print("=" * 72)
    print(f"FACILITY MONITOR — {fund.name}  ({facility.kind} facility)")
    print("=" * 72)
    print(f"[Layer 1] Advance rate / LTV cap : {facility.advance_rate:.0%}")
    print(f"[Layer 1] Borrowing base         : {_f(borrowing_base(fund, facility))}")
    print(f"[Layer 1] Effective limit        : {_f(effective_limit(fund, facility))}"
          f"  (hard cap {_f(facility.limit)})")
    print(f"[Layer 1] Drawn                  : {_f(facility.drawn)}")
    print(f"[Layer 1] Availability           : {_f(availability(fund, facility))}")
    print(f"[Layer 1] Utilization            : {utilization(fund, facility):.1%}")
    print(f"[Layer 1] LTV                    : {ltv(fund, facility):.1%}")
    hf = health_factor(fund, facility)
    hf_label = "inf" if hf == float("inf") else f"{hf:.3f}"
    hf_band = ("safe" if hf >= 1.5 else
               "warning" if hf >= 1.0 else
               "MARGIN CALL")
    print(f"[Layer 1] Health Factor          : {hf_label}  ({hf_band})")
    print(f"[Layer 5] Liquidity coverage     : {liquidity_coverage(fund, facility):.2f}x")
    print("-" * 72)
    print("[Layer 4] Covenant traffic lights")
    for c in covenants.run_all(fund, facility):
        actual = "inf" if c.actual == float("inf") else f"{c.actual:.3f}"
        limit = "inf" if c.limit == float("inf") else f"{c.limit:.3f}"
        print(f"    {DOT[c.status]} {c.name:<28} actual={actual:>8}  limit={limit:>7}")
    if action is not None:
        why = (" — " + ", ".join(reasons)) if reasons else ""
        print("-" * 72)
        print(f"[Layer 4] TRIGGER ACTION: {action}{why}")
    print("=" * 72)


def print_stress_table(rows):
    print("\n[Layer 3] Deterministic stress — NAV haircut sweep")
    print("-" * 74)
    print(f"{'haircut':>8} {'NAV':>10} {'borrow.base':>12} {'avail':>9} {'LTV':>7}  flags")
    print("-" * 74)
    for r in rows:
        flags = []
        if r["bb_deficiency"]:
            flags.append("BB-DEFICIT")
        if r["ltv_breach"]:
            flags.append("LTV-BREACH")
        print(f"{r['haircut']:>7.0%} {r['total_nav']:>10,.1f} {r['borrowing_base']:>12,.1f} "
              f"{r['availability']:>9,.1f} {r['ltv']:>7.1%}  {' '.join(flags)}")
    print("-" * 74)


def print_reverse_stress(ranking):
    """
    Show distance-to-breach for every covenant, ranked. The first row is
    the binding constraint -- the closest the system is to tripping anywhere.
    """
    print("\n[Layer 3] Reverse Stress — distance-to-breach per covenant")
    print("-" * 74)
    print(f"{'rank':>5}  {'covenant':<28} {'NAV haircut at first RED':>30}")
    print("-" * 74)
    for r in ranking:
        if r["breaking_haircut"] is None:
            haircut_str = "  never within tested range"
            rank_str = "—"
        else:
            haircut_str = f"{r['breaking_haircut']:>22.1%}"
            rank_str = f"{r['rank']}"
        tag = "  <- BINDING" if r["rank"] == 1 else ""
        print(f"{rank_str:>5}  {r['covenant']:<28} {haircut_str}{tag}")
    print("-" * 74)


def print_monte_carlo(mc):
    print(f"\n[Layer 3] Monte Carlo — {mc['model']}")
    print("-" * 72)
    print(f"  sims={mc['n_sims']:,}  horizon={mc['horizon_years']:.2f}y")
    print(f"  P(LTV covenant breach)            : {mc['p_ltv_breach']:.1%}")
    print(f"  VaR(95)  of LTV                   : {mc['var95_ltv']:.1%}")
    print(f"  CVaR(99) of LTV  (Expected Shortfall) : {mc['cvar99_ltv']:.1%}")
    print(f"  LTV  p50 / p95 / p99              : "
          f"{mc['ltv_p50']:.1%} / {mc['ltv_p95']:.1%} / {mc['ltv_p99']:.1%}")
    attr = mc.get("sector_attribution", {})
    if attr:
        print("  Sector attribution (avg drawdown when a breach occurs):")
        for s, d in sorted(attr.items(), key=lambda kv: -kv[1]):
            print(f"      {s:<14} {d:>7.1%}")
    print("-" * 72)


def save_stress_chart(rows, max_ltv, path="stress_chart.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("(matplotlib not installed — skipping chart)")
        return None
    hc = [r["haircut"] * 100 for r in rows]
    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.plot(hc, [r["ltv"] * 100 for r in rows], color="#1F3864", lw=2, label="LTV")
    ax1.axhline(max_ltv * 100, color="#C0392B", ls="--", lw=1.5, label=f"Max-LTV ({max_ltv:.0%})")
    ax1.set_xlabel("NAV haircut (%)")
    ax1.set_ylabel("LTV (%)", color="#1F3864")
    ax1.set_title("Stress test: LTV and headroom vs NAV haircut")
    ax2 = ax1.twinx()
    ax2.plot(hc, [r["availability"] for r in rows], color="#27AE60", lw=1.5, label="Availability")
    ax2.axhline(0, color="#999999", ls=":", lw=1)
    ax2.set_ylabel("Availability", color="#27AE60")
    l1, lab1 = ax1.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lab1 + lab2, loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"(saved chart -> {path})")
    return path


def save_reverse_stress_chart(ranking, path="reverse_stress_chart.png"):
    """Horizontal bar chart -- breaking-point haircut per covenant, ranked."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("(matplotlib not installed — skipping reverse stress chart)")
        return None
    items = [r for r in ranking if r["breaking_haircut"] is not None]
    if not items:
        print("(no finite breaking points — skipping reverse stress chart)")
        return None
    items = list(reversed(items))    # so the binding constraint sits on top
    names = [r["covenant"] for r in items]
    haircuts = [r["breaking_haircut"] * 100 for r in items]
    colors = ["#C0392B" if r["rank"] == 1 else "#1F3864" for r in items]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(names, haircuts, color=colors)
    for bar, h in zip(bars, haircuts):
        ax.text(h + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{h:.1f}%", va="center", fontsize=8)
    ax.set_xlabel("NAV haircut at first RED (%)")
    ax.set_title("Reverse stress: distance-to-breach per covenant")
    ax.invert_yaxis()                # top row = binding
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"(saved chart -> {path})")
    return path

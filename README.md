# Fund Finance Facility Risk Monitor

A small, self-contained Python project that simulates a **bank lending to a
private fund** and monitors the risk of that loan — how much can be safely
lent, where the binding constraint actually is, and what happens to the
exposure under sector-correlated stress.

Synthetic data only (no real / confidential data). The point is not to
predict markets; it is to **implement the credit logic a fund-finance desk
uses every day**, as a clean, modular system that can be explained
confidently in an interview.

Fund finance is a *fusion* topic with no off-the-shelf library, so the
system is built as **6 composable layers**, each borrowing a mature
open-source pattern. See [`ARCHITECTURE.md`](ARCHITECTURE.md) and
`figures/architecture.png`.

## The 6 layers

1. **L5 Data ingestion & validation** (`ffrm/data_ingest.py`) — range-check + timestamp inputs.
2. **L2 Credit scoring / PD / EL** (`ffrm/credit_scoring.py`) — Basel III IRB-style: `EL = PD × LGD` per LP, with a continuous eligibility weight (no binary cliff).
3. **L1 Borrowing base & exposure** (`ffrm/borrowing_base.py`) — EL-weighted collateral × advance rate × liquidity haircut → max safe loan; LTV, availability, utilization, and an Aave-style **Health Factor**.
4. **L5 Liquidity** (`ffrm/liquidity.py`) — per-asset haircut by days-to-sell + liquidity-coverage check.
5. **L3 Stress & scenario** (`ffrm/stress.py`) — deterministic NAV sweep, **reverse stress per covenant** (distance-to-breach ranking), and a **multi-factor Monte Carlo** with sector correlations, VaR(95), CVaR(99), and per-sector attribution.
6. **L4 Covenants + trigger engine** (`ffrm/covenants.py`, `ffrm/triggers.py`) — GREEN/AMBER/RED covenants → MONITOR/WARNING/MARGIN CALL/EVENT_OF_DEFAULT, with an HF-aware cure window.

## What changed vs v1 (and what platform each upgrade borrows from)

| # | Upgrade | Platform / standard | EE analogue |
|---|---|---|---|
| 1 | EL = PD × LGD weighting (continuous, not cliff) | Basel III IRB | derating curve |
| 2 | Health Factor as a single risk number | Aave / Compound liquidation | stability margin |
| 3 | Multi-factor Monte Carlo + VaR + CVaR + sector attribution | MSCI Barra factor model / pyfolio risk metrics | cross-PSD noise analysis |
| 4 | Reverse stress per covenant (ranking, not just one number) | Basel SR 11-7 reverse stress | per-loop stability margin |

Key terms it lets you speak to: subscription line vs NAV facility,
borrowing base, advance rate / LTV, expected loss / IRB weighting,
concentration limits, availability / headroom, utilization, **health
factor**, liquidity coverage, covenants, margin call, cure period,
deterministic vs reverse vs Monte Carlo stress, VaR, CVaR / Expected
Shortfall, **multi-factor sector attribution**.

## Run it

New here? Read **START_HERE.md** for a 3-minute, click-by-click guide (Mac & Windows).

```bash
# easiest: double-click 启动报告.command (Mac) or 启动报告.bat (Windows)
# command-line:
python run.py                          # Windows  (Mac: python3 run.py)

# regenerate the PPT deck
python scripts/build_deck.py

# regenerate the architecture diagram
python scripts/make_diagram.py

# run tests
python tests/test_core.py              # 14 sanity tests (also: python -m pytest -q)
```

The three input files live in **sample_data/** and open in Excel/Numbers:
`investors.csv`, `assets.csv`, `facility.csv`. Edit a number, save, and run again.

## Structure

```
fund-finance-risk-monitor/
├── README.md                  # this file
├── 使用说明.md                 # detailed Chinese walkthrough
├── START_HERE.md              # 3-minute click-by-click quick-start
├── ARCHITECTURE.md            # design rationale + EE-finance isomorphism table
├── requirements.txt           # numpy + matplotlib + python-pptx
├── run.py                     # CLI entry point
│
├── 启动报告.command / .bat     # Mac / Win double-click: run + chart + open folder
├── 生成PPT.command / .bat      # Mac / Win double-click: regenerate slides/FFRM-Deck.pptx
│
├── ffrm/                      # 6-layer engine
│   ├── data_ingest.py         # L5 ingest + validate
│   ├── credit_scoring.py      # L2 PD + LGD + EL + eligibility weight (Basel IRB)
│   ├── borrowing_base.py      # L1 borrowing base, LTV, availability, Health Factor (Aave)
│   ├── liquidity.py           # L5 liquidity haircut + coverage
│   ├── covenants.py           # L4 GREEN/AMBER/RED covenants incl. Health Factor
│   ├── triggers.py            # L4 trigger state machine + HF-aware cure window
│   ├── stress.py              # L3 deterministic + reverse + multi-factor MC
│   ├── report.py              # console report + two PNG charts
│   ├── load_csv.py            # CSV loader with friendly errors
│   └── models.py              # dataclasses
│
├── sample_data/               # editable CSVs (open in Excel / Numbers)
│   ├── investors.csv
│   ├── assets.csv
│   └── facility.csv
│
├── data/sample_fund.py        # in-code synthetic fund for scripts/run_monitor.py
├── tests/test_core.py         # 14 tests covering each layer
│
├── scripts/                   # additional entry points
│   ├── run_monitor.py         # orchestrates all 6 layers (synthetic + sub-line)
│   ├── build_deck.py          # generate slides/FFRM-Deck.pptx
│   └── make_diagram.py        # regenerate figures/architecture.svg
│
├── figures/                   # generated images (committed: architecture.*)
│   ├── architecture.png / .svg
│   ├── stress_chart.png       # generated by run.py
│   └── reverse_stress.png     # generated by run.py
│
├── slides/
│   └── FFRM-Deck.pptx         # 12-slide deck, regenerated by build_deck.py
│
└── index.html     # standalone browser UI (no install)
```

## What the sample run shows

Running `python run.py` against the synthetic Project Alpha Fund + NAV facility:

```
[Layer 2] EL-weighted eligibility
  Pension Fund A   A    PD 0.50%  LGD 40%  EL 0.20%  weight 0.98  -> eligible
  Insurer B        AA   PD 0.20%  LGD 35%  EL 0.07%  weight 0.99  -> eligible
  Endowment C      BBP  PD 2.00%  LGD 45%  EL 0.90%  weight 0.91  -> eligible
  Family Office D  NR   PD 10.0%  LGD 50%  EL 5.00%  weight 0.50  -> partial
                                                                    (v1 excluded D entirely)

[Layer 1] Borrowing base 33.75  | drawn 30  | HF 0.956 -> MARGIN CALL today

[Layer 3] Reverse stress (distance-to-breach per covenant)
  rank 1  Health Factor              0.0%   <- BINDING (already RED)
  rank 2  Borrowing-base headroom    11.2%
  rank 3  Utilization                11.2%
  rank 4  Max LTV                    36.9%
  rank 5  Liquidity coverage         80.7%
   —      Asset / sector concentration / Min #assets  never (uniform haircut invariant)

[Layer 3] Multi-factor MC (5 sectors, MSCI Barra-style correlations, 6-month horizon)
  P(LTV breach)        : 0.0%        (vs ~22% under v1's single-shock model)
  VaR(95)              : 19.4%
  CVaR(99)             : 22.1%        <- 1% tail still flirts with the 25% LTV cap
  Sector attribution   : Tech 49% / Financials 41% / Industrials 32% / ...
```

Three things to say in the interview:

1. The **binding constraint is the Health Factor, not LTV** — and the second-tier constraints (BB headroom, utilization) trip at ~11% NAV drop, while LTV is 25 percentage points further away at 37%. Without reverse stress per covenant you would miss this.
2. The multi-factor MC corrects a **40× overstatement** of breach probability in v1's single-shock model. But the CVaR(99) = 22.1% on LTV is the right banker-grade tail metric — close to the 25% LTV covenant, so there *is* a real tail concern. Single-shock MC hid both findings under one P(breach) number.
3. Family Office D contributes 50% of its uncalled commitment under EL weighting (v1: 0%). This is what Basel III IRB-style risk-weighting does: continuous, not a cliff. The narrative on subscription-line collateral changes completely.

## 30-second interview pitch

> "I built a fund-finance facility risk monitor. Because it is a fusion problem
> with no ready library, I decomposed it into six layers — data validation,
> Basel-IRB-style expected-loss weighting on subscription collateral, a
> borrowing base with liquidity haircuts and an Aave-style Health Factor,
> reverse-stress-per-covenant ranking, and a multi-factor Monte Carlo with
> sector correlations giving VaR and CVaR. I am an electrical-engineering
> background, so I treat each piece as one part of a feedback control system:
> covenants are protective relays with an alarm band and a timed trip, the
> advance rate is a derating curve not a cliff, the Health Factor is a
> stability margin, and reverse stress is per-loop stability ranking. One
> result on the synthetic fund: a single-shock MC says 22% breach probability;
> the multi-factor MC says effectively zero — but CVaR(99) on LTV is still 22%,
> right at the covenant. Two views, two stories, both true. It is a lender's
> view: protect principal, rank constraints, don't forecast returns."

## Ways to extend
- A real trained PD model behind `credit_scoring.estimate_pd` (logreg / XGBoost).
- A time axis: capital calls, distributions, and the sub-line → NAV transition; multi-period MC with random walks instead of a single horizon.
- LP-default scenarios (drop the largest LP and re-stress) in the reverse stress engine.
- CCAR-style scenario library: base / adverse / severely adverse parameter sets shown side-by-side.
- A Streamlit / FastAPI dashboard over the same engine.

> Thresholds (advance rates, EL cap, LGDs, covenant limits, sector vols and correlations) are illustrative defaults, not market standards — negotiated per deal in reality.

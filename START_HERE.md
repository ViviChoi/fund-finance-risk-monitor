# START HERE — how to run this (Mac & Windows)

This tool reads three small CSV files, works out how much we could safely lend to a
fund, checks the risk limits, and stress-tests the result. You do not need to know how
to code. It takes about 3 minutes to get running.

---

## Step 1 — install Python (one time only)

Download Python 3 from **https://www.python.org/downloads/** and install it.

- **Windows:** on the first screen of the installer, tick **“Add python.exe to PATH”**, then click Install.
- **Mac:** just run the installer. (Many Macs already have Python 3.)

## Step 2 — open a terminal in this folder

First unzip the project somewhere easy, like your Desktop.

- **Windows:** open the unzipped folder in File Explorer, click the address bar, type `powershell`, and press Enter.
- **Mac:** open the **Terminal** app, type `cd ` (with a space), then drag the unzipped folder onto the Terminal window and press Enter.

## Step 3 — run it

Type **one** of these and press Enter:

- **Windows:** `python run.py`
- **Mac:** `python3 run.py`

That’s it. You’ll see the full report printed in the terminal.

> The double-click launchers (`启动报告.command` on Mac, `启动报告.bat` on Windows)
> install numpy + matplotlib + python-pptx automatically on first run.
> Generated files: `figures/stress_chart.png`, `figures/reverse_stress.png`,
> and `slides/FFRM-Deck.pptx`. Without numpy the engine still works — it falls
> back to a single-shock Monte Carlo (slower, no sector attribution).

---

## The sample data (edit this to try your own numbers)

Everything the tool uses lives in the **`sample_data`** folder as three CSV files you can
open in **Excel** or **Numbers**:

- **`investors.csv`** — the fund’s investors: `name, commitment, uncalled, rating`
- **`assets.csv`** — what the fund owns: `name, sector, nav, liquidity_days`
- **`facility.csv`** — the loan terms: `kind, advance_rate, limit, drawn, cure_days`

To try a scenario: change a number, **Save as CSV** (keep the same name), and run the tool
again. For example, lower an asset’s `nav` to see the value fall and watch the limits move
from green to amber to red.

A couple of notes on the columns:
- `rating` uses `AAA, AA, A, BBB, BB, B, NR` — investors below the cutoff are dropped.
- `advance_rate` is a fraction: `0.20` means we lend at most 20% of value.
- `liquidity_days` is roughly how long that asset takes to sell.

---

## What you’ll see (and how to talk to it)

The report prints in the same order as the slides:

1. **Data check** — confirms the inputs loaded cleanly.
2. **Investor scoring** — Basel-IRB-style: each LP gets a PD, an LGD and an Expected Loss; eligibility is a continuous weight from 0 to 1 (no cliff).
3. **Facility monitor** — the borrowing base, how much is drawn, the **Health Factor** (Aave-style single risk number; HF<1 means margin call), and all the limit traffic lights, ending in an action (MONITOR / WARNING / MARGIN CALL / DEFAULT).
4. **Deterministic stress** — how far values can fall before the first covenant breaks.
5. **Reverse stress per covenant** — ranks every covenant by how far it is from breaching today (the binding constraint is row 1).
6. **Multi-factor Monte Carlo** — sector-correlated shocks; reports P(breach), VaR(95), CVaR(99) and which sectors are driving the breaches when they happen.

All numbers are **illustrative**, from this synthetic sample fund.

---

## If something goes wrong

- **“python is not recognised” / “command not found”** — try `py run.py` (Windows) or `python3 run.py` (Mac). On Windows, re-run the installer and make sure “Add to PATH” is ticked.
- **It can’t find the CSV files** — make sure you’re running `run.py` from inside the unzipped project folder (the one that contains `run.py` and the `sample_data` folder).
- **No chart appears** — that’s fine; the chart is optional. Install matplotlib (above) if you want it.

---

## Prefer a web page? (great for showing HR)

Open **`index.html`** by double-clicking it — it runs in any browser on Mac or
Windows, no install needed. Click **“Load built-in sample”** to see everything instantly, or
**“Choose data folder…”** and pick the `sample_data` folder to load your own CSVs. Drag the
sliders (advance rate, amount drawn, volatility) and watch the traffic lights and charts update
live — a simple, visual way to walk someone through the risk.

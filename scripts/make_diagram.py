#!/usr/bin/env python3
"""Generate a self-contained SVG architecture diagram for the project."""

NAVY = "#1F3864"
ACCENT = "#2E6FB0"
GREEN = "#27AE60"
AMBER = "#E0A106"
RED = "#C0392B"
INK = "#1A1A1A"
GREY = "#5A5A5A"
BG = "#FFFFFF"
BOXBG = "#F4F7FB"

# (layer tag, title, what it does, engineering analogy, tag color)
layers = [
    ("L5", "Data Ingestion and Validation",
     "Load LP / asset data; range-check + timestamp the inputs.",
     "Engineering view: the sensor layer — never trust an un-checked reading.", ACCENT),
    ("L2", "Credit Scoring / PD",
     "Turn LP credit quality into a probability of default; set eligibility.",
     "Engineering view: input qualification — filter out bad inputs.  (ML-ready hook)", ACCENT),
    ("L1", "Borrowing Base and Exposure",
     "Eligible collateral x advance rate x liquidity haircut -> max safe loan; LTV, availability, utilization.",
     "Engineering view: plant state + safety factor (derating).", NAVY),
    ("L3", "Stress and Scenario",
     "Deterministic NAV-haircut sweep (breaking point) + Monte Carlo P(breach).",
     "Engineering view: worst-case fault test + random-disturbance characterisation.", ACCENT),
    ("L4", "Covenant Monitor -> Trigger Engine",
     "Each covenant GREEN / AMBER / RED; engine -> MONITOR / WARNING / MARGIN CALL / DEFAULT (cure period).",
     "Engineering view: protective relay with an alarm band + timed trip.", NAVY),
    ("OUT", "Report and Dashboard",
     "One-page view for the credit committee: metrics, traffic lights, action, charts.",
     "Engineering view: the control-room dashboard.", ACCENT),
]

W = 1040
margin = 40
box_w = W - 2 * margin
box_h = 118
gap = 34
top = 150
H = top + len(layers) * (box_h + gap) + 30

parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI, Helvetica, Arial, sans-serif">'
)
parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>')

# title
parts.append(f'<text x="{margin}" y="56" font-size="30" font-weight="700" fill="{NAVY}">Fund Finance Facility Risk Monitor</text>')
parts.append(f'<text x="{margin}" y="86" font-size="17" fill="{GREY}">A lender&#39;s-eye monitoring system, built as 6 composable layers (synthetic data)</text>')
parts.append(f'<text x="{margin}" y="112" font-size="14" fill="{ACCENT}">Data flows top &#8595; bottom. Each layer = one reusable sub-problem with a borrowed open-source pattern.</text>')

# traffic-light legend (top right)
lx = W - margin - 230
for i, (c, lab) in enumerate([(GREEN, "OK"), (AMBER, "warn"), (RED, "breach")]):
    cx = lx + i * 78
    parts.append(f'<circle cx="{cx}" cy="78" r="8" fill="{c}"/>')
    parts.append(f'<text x="{cx+13}" y="83" font-size="13" fill="{GREY}">{lab}</text>')

for i, (tag, title, desc, analogy, col) in enumerate(layers):
    y = top + i * (box_h + gap)
    # box
    parts.append(f'<rect x="{margin}" y="{y}" width="{box_w}" height="{box_h}" rx="12" fill="{BOXBG}" stroke="{col}" stroke-width="2"/>')
    # left tag stripe
    parts.append(f'<rect x="{margin}" y="{y}" width="78" height="{box_h}" rx="12" fill="{col}"/>')
    parts.append(f'<rect x="{margin+60}" y="{y}" width="18" height="{box_h}" fill="{col}"/>')
    parts.append(f'<text x="{margin+39}" y="{y+box_h/2+8}" font-size="22" font-weight="700" fill="#FFFFFF" text-anchor="middle">{tag}</text>')
    # texts
    tx = margin + 98
    parts.append(f'<text x="{tx}" y="{y+34}" font-size="20" font-weight="700" fill="{INK}">{title}</text>')
    parts.append(f'<text x="{tx}" y="{y+62}" font-size="15" fill="{GREY}">{desc}</text>')
    parts.append(f'<text x="{tx}" y="{y+92}" font-size="14" font-style="italic" fill="{col}">{analogy}</text>')
    # arrow to next
    if i < len(layers) - 1:
        ax = margin + box_w / 2
        ay1 = y + box_h
        ay2 = y + box_h + gap
        parts.append(f'<line x1="{ax}" y1="{ay1}" x2="{ax}" y2="{ay2-8}" stroke="{NAVY}" stroke-width="2.5"/>')
        parts.append(f'<polygon points="{ax-7},{ay2-9} {ax+7},{ay2-9} {ax},{ay2+1}" fill="{NAVY}"/>')

parts.append('</svg>')
svg = "\n".join(parts)

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
out_path = ROOT / "figures" / "architecture.svg"
out_path.parent.mkdir(exist_ok=True)
with open(out_path, "w") as f:
    f.write(svg)
print(f"wrote {out_path} ({len(svg)} bytes)")

"""
LAYER 5 (part A) — DATA INGESTION.

In a real desk, "getting the right data at the right time from the right source"
is the critical success factor. Marks are volatile and arrive from many sources,
so before we compute anything we VALIDATE the inputs and stamp them with a time.

This module returns a Fund plus a DataSnapshot describing data quality.
Engineering analogy: this is the sensor layer — never trust a reading you have
not range-checked and time-stamped.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

VALID_RATINGS = {"AAA", "AA", "A", "BBB", "BB", "B", "CCC", "NR"}


@dataclass
class DataSnapshot:
    timestamp: str
    source: str
    n_lps: int
    n_assets: int
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.warnings) == 0


def validate(fund, source: str = "synthetic") -> DataSnapshot:
    """Range-check the inputs and return a data-quality snapshot."""
    warnings = []
    for lp in fund.lps:
        if lp.uncalled < 0 or lp.commitment < 0:
            warnings.append(f"LP {lp.name}: negative commitment/uncalled")
        if lp.uncalled > lp.commitment:
            warnings.append(f"LP {lp.name}: uncalled > commitment")
        if lp.rating not in VALID_RATINGS:
            warnings.append(f"LP {lp.name}: unknown rating {lp.rating!r}")
    for a in fund.assets:
        if a.nav < 0:
            warnings.append(f"Asset {a.name}: negative NAV")
        if a.liquidity_days <= 0:
            warnings.append(f"Asset {a.name}: non-positive liquidity_days")
    return DataSnapshot(
        timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        source=source,
        n_lps=len(fund.lps),
        n_assets=len(fund.assets),
        warnings=warnings,
    )

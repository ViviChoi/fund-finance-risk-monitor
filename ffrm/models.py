"""
Core data models. Four objects everything is built from.

New vs the first version:
  - Asset now carries `liquidity_days` (how long to sell it) -> feeds Layer 5.
  - LP can carry a `pd` (probability of default); if not set, Layer 2 estimates it.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LP:
    """A Limited Partner (investor) who has promised capital to the fund."""
    name: str
    commitment: float            # total promised capital
    uncalled: float              # promised but not yet drawn (sub-line collateral)
    rating: str                  # "AAA","AA","A","BBB","BB","B","NR"
    pd: Optional[float] = None   # probability of default (0..1); estimated if None


@dataclass
class Asset:
    """A portfolio investment, marked at NAV, with a liquidity profile."""
    name: str
    sector: str
    nav: float                   # current net asset value (the "mark")
    liquidity_days: float = 30   # estimated days to liquidate at fair value


@dataclass
class Fund:
    """The borrower: investors (LPs) + holdings (Assets)."""
    name: str
    lps: List[LP]
    assets: List[Asset]

    @property
    def total_uncalled(self) -> float:
        return sum(lp.uncalled for lp in self.lps)

    @property
    def total_nav(self) -> float:
        return sum(a.nav for a in self.assets)


@dataclass
class Facility:
    """
    The loan the bank provides.
      kind          : "subscription" (vs uncalled commitments) or "nav" (vs NAV)
      advance_rate  : sub-line -> % of eligible commitments;  nav -> max LTV cap
      limit         : hard cap on facility size
      drawn         : amount currently borrowed
      cure_days     : grace period to fix a breach before it becomes a default
    """
    kind: str
    advance_rate: float
    limit: float
    drawn: float
    cure_days: int = 10

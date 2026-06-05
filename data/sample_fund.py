"""
Synthetic sample data only — no real/confidential data.
Edit freely to explore scenarios.
"""

from ffrm.models import LP, Asset, Fund, Facility


def sample_fund() -> Fund:
    lps = [
        LP("Pension Fund A",  commitment=100, uncalled=40, rating="A"),
        LP("Insurer B",       commitment=80,  uncalled=30, rating="AA"),
        LP("Endowment C",     commitment=50,  uncalled=20, rating="BBB"),
        LP("Family Office D", commitment=30,  uncalled=15, rating="NR"),  # PD too high -> excluded
    ]
    assets = [
        Asset("TechCo",       "Technology",  nav=60, liquidity_days=60),
        Asset("HealthCo",     "Healthcare",  nav=40, liquidity_days=90),
        Asset("IndustrialCo", "Industrials", nav=35, liquidity_days=120),
        Asset("RetailCo",     "Consumer",    nav=25, liquidity_days=45),
        Asset("FinCo",        "Financials",  nav=30, liquidity_days=30),
    ]
    return Fund("Project Alpha Fund", lps=lps, assets=assets)


def sample_nav_facility() -> Facility:
    return Facility(kind="nav", advance_rate=0.20, limit=50, drawn=30, cure_days=10)


def sample_subscription_facility() -> Facility:
    return Facility(kind="subscription", advance_rate=0.90, limit=60, drawn=40, cure_days=10)

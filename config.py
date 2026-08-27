"""
config.py
Central configuration for the GIFT360 backend -- one place to look up the
database path, the session secret, and the assumptions behind the demo
"Buy" simulator, instead of hunting for magic numbers scattered across
route files.
"""

import os
from pathlib import Path

# --- Application --------------------------------------------------------

# Read from the environment first so a real deployment can override it
# without touching code; falls back to the original demo value so local
# runs and the current Render deployment behave exactly as before.
SECRET_KEY = os.environ.get("SECRET_KEY", "gift360-demo-secret-key-not-for-production")

DB_PATH = Path(os.environ.get("GIFT360_DB_PATH", "gift_city_amc_funds.db"))

# --- Demo "Buy" simulator -------------------------------------------------
# These mirror the real GIFT City outbound remittance cost structure used by
# IFSCA distributor platforms: a flat per-transaction fee, an indicative
# USD/INR conversion rate, and GST charged on the standard 1% forex-
# conversion service margin (the actual RBI/GST treatment for LRS
# remittances). They are NOT a real bank/FX feed -- purely for a believable,
# internally-consistent demo quote. See services/orders.py for how they're
# used and demo_holdings' table comment in database.py for the full caveat.
MIN_BUY_AMOUNT_USD = 500.0  # fallback floor only, when a fund has no real minimum-investment data at all
DEMO_TXN_FEE_USD = 2.0
DEMO_FX_RATE = 88.50
DEMO_LINKED_BANK = "HDFC Bank ****1234"

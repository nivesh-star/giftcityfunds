"""
config.py
Central configuration for the GIFT360 backend.

The SQLite database path is gone: fund data now comes from the shared
mf-engine-v2 API (services/mf_engine.py), and the demo account tables moved
to Postgres (services/demo_db.py, configured via DEMO_DATABASE_URL).

The DEMO_* constants below are unchanged.
"""

import os

# SECRET_KEY signs Flask's session cookie, which is what keeps a demo user
# logged in. A public deployment must never run on a committed default --
# generate one with:
#     python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.environ.get("SECRET_KEY", "gift360-dev-only-change-in-production")

# --- Demo "Buy" simulator -------------------------------------------------
# These mirror the real GIFT City outbound remittance cost structure used by
# IFSCA distributor platforms: a flat per-transaction fee, an indicative
# USD/INR conversion rate, and GST charged on the standard 1% forex-
# conversion service margin (the actual RBI/GST treatment for LRS
# remittances). They are NOT a real bank/FX feed -- purely for a believable,
# internally-consistent demo quote. See services/orders.py for how they're
# used.
MIN_BUY_AMOUNT_USD = 500.0   # fallback floor only, when a fund has no real minimum-investment data at all
DEMO_TXN_FEE_USD = 2.0
DEMO_FX_RATE = 88.50
DEMO_LINKED_BANK = "HDFC Bank ****1234"

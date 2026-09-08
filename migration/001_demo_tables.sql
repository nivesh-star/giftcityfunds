-- GIFT360 demo account / portfolio tables (Postgres)
--
-- These replace the SQLite tables of the same names. Fund data is NOT here --
-- funds, NAVs, holdings and allocations all come from the shared mf-engine-v2
-- API. These three tables only hold demo-specific rows that have no home in
-- that API.
--
-- EVERYTHING IN demo_holdings IS A SIMULATION. No real money moves, no real
-- units are allotted, nothing is sent to any AMC, bank or transfer agent.
-- The rows exist so the demo portfolio page can show a realistic position.
--
-- Note demo_holdings has no foreign key to a funds table: fund data lives in
-- a different database entirely (the mf-engine production DB), so fund_id
-- here is an unenforced reference to gift_city_funds.id over there.
--
-- Safe to re-run: every statement uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS demo_users (
    user_id       SERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Mirrors what a real AMC folio application asks for, but NOTHING here is
-- verified against any bank or registry -- there is no KYC, no penny-drop
-- verification, no regulatory basis for holding it. It exists so a demo
-- account looks like a complete investor record.
CREATE TABLE IF NOT EXISTS demo_investor_profile (
    profile_id            SERIAL PRIMARY KEY,
    user_id               INTEGER NOT NULL UNIQUE
                          REFERENCES demo_users(user_id) ON DELETE CASCADE,
    mobile_number         TEXT,
    bank_name             TEXT,
    account_number        TEXT,
    ifsc_code             TEXT,
    nominee_name          TEXT,
    nominee_relationship  TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS demo_holdings (
    holding_id      SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES demo_users(user_id) ON DELETE CASCADE,
    fund_id         INTEGER NOT NULL,  -- gift_city_funds.id in the mf-engine DB
    units           NUMERIC NOT NULL,
    invested_amount NUMERIC NOT NULL,
    buy_nav         NUMERIC NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    purchase_date   TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          TEXT NOT NULL DEFAULT 'completed'
);

CREATE INDEX IF NOT EXISTS idx_demo_holdings_user
    ON demo_holdings (user_id, purchase_date DESC);

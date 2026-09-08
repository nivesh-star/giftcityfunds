"""
app.py
GIFT360 -- GIFT City (IFSC) Funds Intelligence Platform.

This is the application's single entry point. Its only job is to build the
Flask app and wire the blueprints that make up the whole backend onto it --
every actual route lives in routes/, every piece of reusable logic lives in
services/. Nothing else should be added to this file; if it starts growing,
that's a sign new logic belongs in one of those modules instead.

Layout:
    config.py             application constants (secret key)
    services/mf_engine.py the one place that talks to the mf-engine-v2 API
    services/adapters.py  maps the API's shape to the frontend's field names
    content/faqs.py       static FAQ copy for the outbound/inbound pages
    services/funds.py     fund-related helpers (slugs, plan labels)
    services/demo_db.py   Postgres connection for the demo account tables
    routes/auth.py        /login, /signup, /logout + the @login_required guard
    routes/pages.py       server-rendered HTML pages
    routes/api.py         the JSON REST API under /api

Fund data comes from the shared mf-engine-v2 API (app2.mfapis.club), so
GIFT360 and Zinni serve identical numbers from one source of truth. The demo
account / Buy simulator keeps its own small set of tables, moved from a local
SQLite file to Postgres so it works on a serverless host.
"""

from __future__ import annotations

import os

from flask import Flask

from config import SECRET_KEY
from routes.api import api_bp
from routes.auth import auth_bp
from routes.pages import pages_bp


def create_app() -> Flask:
    """Application factory: builds and returns a fully configured Flask app.
    Kept as a function (rather than only a bare module-level app) so tests
    or a future second entry point can build a fresh instance on demand."""
    flask_app = Flask(__name__, static_folder="static", template_folder="templates")
    flask_app.secret_key = SECRET_KEY

    flask_app.register_blueprint(pages_bp)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(api_bp, url_prefix="/api")

    return flask_app


# Module-level `app` so `python app.py` (local dev, below), `gunicorn app:app`
# and Vercel's api/index.py entry point all work unchanged.
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 70)
    print("  GIFT360 — GIFT City (IFSC) Funds Intelligence Platform")
    print(f"  Serving live on port {port}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False)

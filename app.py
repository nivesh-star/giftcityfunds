"""
app.py
GIFT360 -- GIFT City (IFSC) Funds Intelligence Platform.

This is the application's single entry point. Its only job is to build the
Flask app and wire the three blueprints that make up the whole backend onto
it -- every actual route lives in routes/, every piece of reusable logic
lives in services/, and every database access goes through db.py. Nothing
else should be added to this file; if it starts growing, that's a sign new
logic belongs in one of those modules instead.

Layout:
    config.py          constants: DB path, secret key, demo "Buy" assumptions
    db.py               the one place that opens a SQLite connection
    content/faqs.py     static FAQ copy for the outbound/inbound pages
    services/funds.py   fund-related business logic (slugs, plan labels, min-investment parsing)
    services/orders.py  the demo "Buy" simulator (quotes, folio numbers, validation)
    routes/auth.py      /login, /signup, /logout + the @login_required guard
    routes/pages.py     server-rendered HTML pages
    routes/api.py       the JSON REST API under /api
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


# Module-level `app` so both `python app.py` (local dev, below) and
# `gunicorn app:app` (the production entry point on Render) work unchanged.
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 70)
    print("  GIFT360 — GIFT City (IFSC) Funds Intelligence Platform")
    print(f"  Serving live on port {port}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False)

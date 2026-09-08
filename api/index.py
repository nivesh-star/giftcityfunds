"""
api/index.py

Vercel serverless entry point. Vercel's Python runtime looks for a WSGI
callable named `app` inside the api/ directory -- this just imports the
existing Flask app from the project root, so app.py stays the single place
the application is actually built.

Nothing here is Vercel-specific beyond the import path fix: the same app.py
still runs unchanged locally (`python app.py`) and under gunicorn.
"""

import os
import sys

# Vercel executes this file from inside api/, so the project root (where
# app.py, routes/, services/, templates/ live) isn't on the import path by
# default. Adding it explicitly keeps every existing `from routes...` /
# `from services...` import working untouched.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402

# Vercel's @vercel/python runtime picks this up as the WSGI handler.
# The name must be `app` (or `handler`) for it to be detected.
__all__ = ["app"]

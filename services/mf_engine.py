"""
services/mf_engine.py

The one place that talks to the mf-engine-v2 API (app2.mfapis.club).
Replaces db.py's role as the data source -- GIFT360 no longer reads its own
SQLite database for fund data; it fetches from the shared company API so
Zinni and GIFT360 both serve the same numbers from the same place.

Credentials never reach the browser: this module runs server-side only, and
routes/api.py proxies the data out to the frontend. Set them via env vars --
nothing is hardcoded here:

    MF_ENGINE_BASE_URL       defaults to https://app2.mfapis.club
    MF_ENGINE_IDENTIFIER     partner login identifier (email or mobile)
    MF_ENGINE_PASSWORD       partner password

The token is cached in memory and reused until it expires or a request comes
back 401, at which point it re-logs in once and retries. That keeps the
common case to a single API call rather than logging in per request.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, List, Optional

import requests

BASE_URL = os.environ.get("MF_ENGINE_BASE_URL", "https://app2.mfapis.club").rstrip("/")
IDENTIFIER = os.environ.get("MF_ENGINE_IDENTIFIER")
PASSWORD = os.environ.get("MF_ENGINE_PASSWORD")

# How long to trust a cached token before proactively re-logging in. The API
# doesn't document the real TTL, so this is deliberately conservative -- a
# 401 mid-flight is handled separately by _request() retrying once.
TOKEN_TTL_SECONDS = int(os.environ.get("MF_ENGINE_TOKEN_TTL", 30 * 60))

# How long to cache the fund list. The underlying data updates once a day via
# the scraper pipeline, so re-fetching on every page load would be wasteful.
FUND_LIST_TTL_SECONDS = int(os.environ.get("MF_ENGINE_FUND_CACHE_TTL", 5 * 60))

# SERVERLESS NOTE (Vercel): these caches are per-process, in memory. Vercel
# reuses warm containers between requests, so caching does work -- but each
# concurrent instance keeps its own copy, and a cold start begins with an
# empty cache (meaning one extra login call). That's an acceptable cost at
# this traffic level. If login volume ever becomes a problem, the fix is an
# external cache (Vercel KV / Redis) rather than longer TTLs, since longer
# TTLs just mean staler data per instance.

_token: Optional[str] = None
_token_fetched_at: float = 0.0
_token_lock = threading.Lock()

_fund_list_cache: Optional[List[Dict[str, Any]]] = None
_fund_list_fetched_at: float = 0.0
_fund_list_lock = threading.Lock()

_session = requests.Session()


class MfEngineError(RuntimeError):
    """Raised when the API can't be reached or returns an unexpected shape.
    routes/api.py turns this into a 502 rather than leaking a stack trace."""


def _login() -> str:
    """Fetches a fresh partner bearer token."""
    if not IDENTIFIER or not PASSWORD:
        raise MfEngineError(
            "MF_ENGINE_IDENTIFIER / MF_ENGINE_PASSWORD are not set. "
            "Refusing to guess credentials."
        )
    try:
        resp = _session.post(
            f"{BASE_URL}/api/v2/partner/login",
            json={"identifier": IDENTIFIER, "password": PASSWORD},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise MfEngineError(f"Could not reach mf-engine login: {exc}") from exc

    if resp.status_code != 200:
        raise MfEngineError(f"Login failed with HTTP {resp.status_code}")

    payload = resp.json()
    token = (payload.get("data") or {}).get("accessToken")
    if not token:
        raise MfEngineError(f"Login response had no accessToken: {payload.get('message')}")
    return token


def _get_token(force_refresh: bool = False) -> str:
    global _token, _token_fetched_at
    with _token_lock:
        expired = (time.time() - _token_fetched_at) > TOKEN_TTL_SECONDS
        if force_refresh or _token is None or expired:
            _token = _login()
            _token_fetched_at = time.time()
        return _token


def _request(path: str) -> Any:
    """GETs an authenticated endpoint, re-logging in once on a 401.
    Returns the unwrapped `data` payload."""
    for attempt in (1, 2):
        token = _get_token(force_refresh=(attempt == 2))
        try:
            resp = _session.get(
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise MfEngineError(f"Could not reach mf-engine {path}: {exc}") from exc

        if resp.status_code == 401 and attempt == 1:
            continue  # token likely expired -- retry once with a fresh one
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise MfEngineError(f"mf-engine {path} returned HTTP {resp.status_code}")

        payload = resp.json()
        # The GIFT City endpoints wrap results as {"data": ...}
        return payload.get("data") if isinstance(payload, dict) and "data" in payload else payload

    raise MfEngineError(f"mf-engine {path} kept returning 401 after re-authenticating")


def fetch_funds(force: bool = False) -> List[Dict[str, Any]]:
    """Returns the full GIFT City fund list, cached briefly in memory."""
    global _fund_list_cache, _fund_list_fetched_at
    with _fund_list_lock:
        fresh = (time.time() - _fund_list_fetched_at) < FUND_LIST_TTL_SECONDS
        if not force and _fund_list_cache is not None and fresh:
            return _fund_list_cache
        data = _request("/api/v2/gift_city")
        if not isinstance(data, list):
            raise MfEngineError("Expected a list of funds from /api/v2/gift_city")
        _fund_list_cache = data
        _fund_list_fetched_at = time.time()
        return data


def fetch_fund(fund_id: int) -> Optional[Dict[str, Any]]:
    """Returns one fund with its nested detail (holdings, allocations,
    performance, share classes, nav_history, ...). None if not found."""
    return _request(f"/api/v2/gift_city/{fund_id}")

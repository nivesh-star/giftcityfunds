"""
routes/pages.py
Server-rendered HTML pages: the dashboard, the outbound/inbound fund
listing pages, and each fund's own detail page. The JSON API those pages
call into lives in routes/api.py instead.

DATA SOURCE CHANGE: these routes no longer open a SQLite connection. Fund
data comes from the shared mf-engine-v2 API via services/mf_engine.py, the
same source routes/api.py uses, so GIFT360 and Zinni serve identical numbers.

The demo portfolio page is kept, gated behind the demo login as before --
only its storage moved from SQLite to Postgres (services/demo_db.py), since
SQLite can't work on Vercel.
"""

from typing import Optional

from flask import Blueprint, redirect, render_template, url_for

from content.faqs import FAQ_SOURCE_ATTRIBUTION, INBOUND_FAQS, OUTBOUND_FAQS
from routes.auth import login_required
from services import adapters
from services.funds import slugify
from services.mf_engine import MfEngineError, fetch_funds

pages_bp = Blueprint("pages", __name__)


def _funds_by_flow(flow_type: str):
    """Returns funds for one capital-flow direction, in the frontend's
    expected field shape. On an upstream failure the page still renders --
    with an empty list and a flag the template can use to show a notice --
    rather than 500ing the whole page."""
    try:
        raw = fetch_funds()
    except MfEngineError:
        return [], True
    funds = [adapters.fund_summary(f) for f in raw if f.get("fund_flow_type") == flow_type]
    funds.sort(key=lambda f: (f.get("fund_name") or ""))
    return funds, False


@pages_bp.route("/")
def index():
    """Renders the main GIFT360 Dashboard UI."""
    return render_template("index.html")


@pages_bp.route("/gift-city-outbound")
def gift_city_outbound():
    """Dedicated page for outbound GIFT City funds (India/GIFT-domiciled
    capital investing abroad), with FAQ content specific to outbound
    investing (churn tax, lock-ins, AIF/PMS/Retail structure differences)."""
    funds, data_unavailable = _funds_by_flow("outbound")
    return render_template(
        "flow_page.html",
        flow_type="outbound",
        page_title="GIFT City Outbound Funds",
        page_subtitle="India/GIFT-domiciled capital investing abroad — AIFs, PMS, and retail fund strategies for global investing.",
        funds=funds,
        data_unavailable=data_unavailable,
        faqs=OUTBOUND_FAQS,
        faq_source=FAQ_SOURCE_ATTRIBUTION,
        other_flow_url="/gift-city-inbound",
        other_flow_label="Inbound Funds",
    )


@pages_bp.route("/gift-city-inbound")
def gift_city_inbound():
    """Dedicated page for inbound GIFT City funds (foreign/NRI capital
    investing into India via GIFT), with FAQ content specific to inbound
    investing (K1 compliance, IFSCA tax benefits, investor eligibility)."""
    funds, data_unavailable = _funds_by_flow("inbound")
    return render_template(
        "flow_page.html",
        flow_type="inbound",
        page_title="GIFT City Inbound Funds",
        page_subtitle="Foreign and NRI capital investing into India through GIFT City IFSC — fund houses, strategies, and tax structure.",
        funds=funds,
        data_unavailable=data_unavailable,
        faqs=INBOUND_FAQS,
        faq_source=FAQ_SOURCE_ATTRIBUTION,
        other_flow_url="/gift-city-outbound",
        other_flow_label="Outbound Funds",
    )


@pages_bp.route("/portfolio")
@login_required
def portfolio():
    """The logged-in demo user's simulated portfolio page. Data comes from
    /api/portfolio (routes/api.py); this route only renders the shell."""
    return render_template("portfolio.html")


@pages_bp.route("/fund/<int:fund_id>")
@pages_bp.route("/fund/<int:fund_id>/<slug>")
def fund_detail_page(fund_id: int, slug: Optional[str] = None):
    """Full standalone page for a single fund -- gives every fund its own
    shareable URL, named after the fund rather than just its numeric id. A
    bare /fund/<id> (or a stale/incorrect slug) 301-redirects to the
    canonical named URL so old links keep working.

    Looked up from the cached fund list rather than a per-fund API call:
    this route only needs the name and AMC for the page shell, and the
    detail page's own JavaScript fetches the full record from
    /api/fund/<id> anyway."""
    try:
        raw = fetch_funds()
    except MfEngineError:
        return render_template("fund_not_found.html"), 503

    fund = next((f for f in raw if f.get("id") == fund_id), None)
    if not fund:
        return render_template("fund_not_found.html"), 404

    correct_slug = slugify(fund["fund_name"])
    if slug != correct_slug:
        return redirect(
            url_for("pages.fund_detail_page", fund_id=fund_id, slug=correct_slug), code=301
        )

    return render_template(
        "fund_detail.html",
        fund_id=fund_id,
        fund_name=fund["fund_name"],
        amc_name=fund.get("amc_name") or (fund.get("amc") or {}).get("name"),
    )

"""
routes/pages.py
Server-rendered HTML pages: the dashboard, the outbound/inbound fund
listing pages, the demo portfolio page, and each fund's own detail page.
The JSON API those pages call into lives in routes/api.py instead.
"""

from typing import Optional

from flask import Blueprint, redirect, render_template, url_for

from content.faqs import FAQ_SOURCE_ATTRIBUTION, INBOUND_FAQS, OUTBOUND_FAQS
from db import get_db_connection
from routes.auth import login_required
from services.funds import slugify

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    """Renders the main GIFT360 Dashboard UI."""
    return render_template("index.html")


@pages_bp.route("/gift-city-outbound")
def gift_city_outbound():
    """Dedicated page for outbound GIFT City funds (India/GIFT-domiciled
    capital investing abroad), with FAQ content specific to outbound
    investing (churn tax, lock-ins, AIF/PMS/Retail structure differences)."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM funds WHERE fund_flow_type = 'outbound' ORDER BY fund_name"
        ).fetchall()
        funds = [dict(r) for r in rows]
    return render_template(
        "flow_page.html",
        flow_type="outbound",
        page_title="GIFT City Outbound Funds",
        page_subtitle="India/GIFT-domiciled capital investing abroad — AIFs, PMS, and retail fund strategies for global investing.",
        funds=funds,
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
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM funds WHERE fund_flow_type = 'inbound' ORDER BY fund_name"
        ).fetchall()
        funds = [dict(r) for r in rows]
    return render_template(
        "flow_page.html",
        flow_type="inbound",
        page_title="GIFT City Inbound Funds",
        page_subtitle="Foreign and NRI capital investing into India through GIFT City IFSC — fund houses, strategies, and tax structure.",
        funds=funds,
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
    """Full standalone page for a single fund (was previously a modal
    overlay on the dashboard) -- gives every fund its own shareable URL,
    named after the fund rather than just its numeric id. A bare /fund/<id>
    (or a stale/incorrect slug) 301-redirects to the canonical named URL so
    old links keep working."""
    with get_db_connection() as conn:
        fund = conn.execute(
            "SELECT fund_id, fund_name, amc_name FROM funds WHERE fund_id = ?", (fund_id,)
        ).fetchone()
    if not fund:
        return render_template("fund_not_found.html"), 404

    correct_slug = slugify(fund["fund_name"])
    if slug != correct_slug:
        return redirect(url_for("pages.fund_detail_page", fund_id=fund_id, slug=correct_slug), code=301)

    return render_template(
        "fund_detail.html", fund_id=fund_id, fund_name=fund["fund_name"], amc_name=fund["amc_name"]
    )

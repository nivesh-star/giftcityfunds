"""
content/events.py
GIFT City-related events GIFT360 surfaces for visitors -- currently just the
webinars/sessions run by GIFT City AMCs themselves, listed with a link to
their actual registration page (Luma, in this case) rather than reproduced
as a GIFT360-hosted event.

`context_note` is a short, cited summary of why the event's topic matters,
drawn from published third-party coverage (see `context_source_url` /
`context_source_name`) -- not GIFT360's own editorial claim, so it's kept
separate from the event's own official description.
"""

EVENTS = [
    {
        "slug": "gift-city-alternative-investments-ppfas-webinar",
        "title": "Understanding Alternative Investments & Opportunities in GIFT City",
        "badge": "Webinar",
        "host": "PPFAS GIFT Fund",
        "speakers": "Akshay Falgunia (Fund Manager, PPFAS GIFT Fund) and Hema Thakkar (Head, Business Development -- Alternatives)",
        "date_display": "Fri, 18 Sep 2026",
        "time_display": "4:00 -- 5:00 PM IST",
        "format_display": "Online",
        "card_description": "PPFAS GIFT Fund's Akshay Falgunia and Hema Thakkar unpack the alternative investments landscape in GIFT City -- strategy, portfolio construction, and where the space is headed.",
        "detail_description": "An exclusive session with PPFAS GIFT City's own fund and business development teams, covering the PPFAS GIFT Fund's investment strategy, the broader alternatives ecosystem in GIFT City, market perspectives, portfolio construction insights, and where alternatives in India are headed next.",
        "register_url": "https://luma.com/g9yh8zd4",
        "context_note": "Rupee savings held against a future dollar goal -- a child's overseas degree, a home abroad -- quietly lose ground to currency depreciation over time. GIFT City's USD-denominated funds, accessed via the Liberalised Remittance Scheme, let that saving happen in the same currency it will eventually be spent in, which is the kind of structure this session's alternatives discussion sits inside.",
        "context_source_name": "Outlook Money",
        "context_source_url": "https://www.outlookmoney.com/spotlight/you-have-been-saving-in-rupees-for-a-dollar-future-and-that-is-the-problem",
    },
]

"""
content/faqs.py
FAQ copy for the /gift-city-outbound and /gift-city-inbound pages.

Sir asked that outbound and inbound GIFT City funds be presented as
distinct sections (mirroring thefynprint.com's own /gift-city-outbound and
/gift-city-inbound pages), each with its own FAQ content, rather than only
a badge inside the shared Tier 1/Tier 2 dashboard. routes/pages.py renders
that split; funds are classified via `fund_flow_type` on the `funds` table
(set only when explicitly confirmed against a fund's own factsheet or a
corroborating source such as thefynprint's trackers -- never inferred from
a fund's name alone), so a fund with no confirmed classification simply
does not appear on either page instead of being guessed into one.
"""

OUTBOUND_FAQS = [
    {
        "question": "What are GIFT City outbound funds?",
        "answer": [
            "Outbound funds in GIFT City IFSC allow Indian and NRI investors to invest in global markets through fund structures domiciled in India's IFSC.",
            "These funds invest in international equities, ETFs, and alternative assets across the US, Europe, Asia, and emerging markets.",
            "They provide a regulated, tax-efficient route for global diversification without needing an overseas brokerage account.",
        ],
    },
    {
        "question": "What is the difference between AIFs, PMS, and Retail funds in GIFT City?",
        "answer": [
            "AIFs (Alternative Investment Funds) are pooled investment vehicles for sophisticated investors — typically with higher minimum investments and lock-in periods.",
            "PMS (Portfolio Management Services) offer personalised portfolio management with a minimum ticket size of $75,000 in GIFT City.",
            "Retail funds have lower entry barriers (as low as $5,000) and are structured as open-ended funds accessible to a broader investor base.",
        ],
    },
    {
        "question": "What are the tax implications of investing through GIFT City outbound funds?",
        "answer": [
            "Funds structured through Irish-domiciled UCITS or Cayman routes can avoid churn tax — no tax on internal portfolio rebalancing.",
            "Some fund structures may be subject to fund-level taxation where investor exits can increase tax burden for remaining investors.",
            "Tax treatment varies by fund structure — AIF, PMS, and retail fund routes each have different implications. Consult a tax advisor.",
        ],
    },
    {
        "question": "What is 'churn tax' and why does it matter?",
        "answer": [
            "Churn tax refers to capital gains tax triggered when a fund buys and sells securities within its portfolio.",
            "Funds routed through Cayman Islands or Irish UCITS structures can avoid this tax, making them more tax-efficient.",
            "Direct PMS strategies may be subject to churn tax since trades happen in the investor's name, potentially reducing net returns.",
        ],
    },
    {
        "question": "What are the lock-in periods for GIFT City outbound funds?",
        "answer": [
            "AIFs typically have lock-in periods ranging from 2 to 4 years depending on the fund strategy.",
            "PMS strategies generally offer more flexibility with lower or no lock-in periods and zero exit loads.",
            "Retail funds usually have no lock-in and offer daily or weekly redemption options.",
        ],
    },
    {
        "question": "How do I choose between different GIFT City outbound fund options?",
        "answer": [
            "Consider your investment horizon — AIFs suit long-term investors comfortable with 2-4 year lock-ins.",
            "Evaluate geographic allocation — some funds focus on US markets while others offer broader global diversification.",
            "Compare fee structures, tax efficiency (churn tax vs fund-level tax), and minimum ticket sizes to match your requirements.",
        ],
    },
]

INBOUND_FAQS = [
    {
        "question": "What is GIFT City and why are inbound funds important?",
        "answer": [
            "GIFT City (Gujarat International Finance Tec-City) is India's first International Financial Services Centre (IFSC) located in Gandhinagar, Gujarat.",
            "Inbound funds in GIFT City allow foreign portfolio investors and NRIs to invest in Indian markets through a regulatory-friendly IFSC framework.",
            "These funds enjoy benefits like tax exemptions, no STT, no CTT, and a simplified compliance structure under IFSCA regulations.",
        ],
    },
    {
        "question": "How are GIFT City inbound funds different from regular mutual funds?",
        "answer": [
            "GIFT City inbound funds are denominated in foreign currencies (primarily USD) and regulated by IFSCA instead of SEBI.",
            "They offer tax advantages — no capital gains tax, no STT, no dividend distribution tax for eligible investors.",
            "They provide a bridge for global investors to access Indian equities, debt, and alternative assets under international best practices.",
        ],
    },
    {
        "question": "Who can invest in GIFT City inbound funds?",
        "answer": [
            "Non-Resident Indians (NRIs) and Persons of Indian Origin (PIOs) can invest through these funds.",
            "Foreign Portfolio Investors (FPIs) and institutional investors can access Indian markets via GIFT City.",
            "Some funds also allow resident Indians who qualify under the Liberalised Remittance Scheme (LRS).",
        ],
    },
    {
        "question": "What are the tax benefits of investing through GIFT City?",
        "answer": [
            "No Securities Transaction Tax (STT) or Commodities Transaction Tax (CTT) on transactions.",
            "Exemption from capital gains tax for units held in IFSC for 10 years under certain conditions.",
            "No Dividend Distribution Tax — dividends are tax-free at the fund level.",
            "GST exemptions on certain financial services within the IFSC.",
        ],
    },
    {
        "question": "What is K1 compliance and why does it matter for US NRIs?",
        "answer": [
            "K-1 is an IRS tax form used to report a partner's share of income, deductions, and credits from a partnership or S corporation.",
            "For US-based NRIs, investing in K1-compliant funds simplifies tax reporting to the IRS.",
            "Non-K1 funds may require complex PFIC (Passive Foreign Investment Company) reporting, which can be burdensome.",
            "K1-compliant GIFT City funds are structured to issue Schedule K-1 forms, making US tax filing straightforward.",
        ],
    },
    {
        "question": "What types of funds operate from GIFT City?",
        "answer": [
            "Equity funds investing in Indian listed securities (large, mid, small cap) through feeder structures.",
            "Debt funds targeting Indian government securities and corporate bonds.",
            "Hybrid and multi-asset funds combining equity, debt, and alternative strategies.",
            "Category III AIFs offering long-short, arbitrage, and other sophisticated strategies.",
        ],
    },
]

# Sourced from thefynprint.com/gift-city-outbound and /gift-city-inbound (both
# pages state "Data sourced from fund house disclosures ... may be subject to
# delays" -- carried here verbatim as our own attribution to that source).
FAQ_SOURCE_ATTRIBUTION = "FAQ content sourced from thefynprint.com's GIFT City Outbound/Inbound Funds Trackers."

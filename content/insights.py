"""
content/insights.py
Editorial copy for the /insights section -- GIFT360's own explainer and
news-analysis articles on GIFT City IFSC investing, written in-house
(not reproduced from any outside publisher) so the site has a citable,
plain-English reference for the regulatory and product concepts the
rest of the dashboard assumes readers already know.

Each article's `body` is a small list of typed blocks the templates
walk in order:
    {"type": "p",  "text": "..."}                 -- paragraph
    {"type": "h2", "text": "..."}                  -- section heading
    {"type": "ul", "points": ["...", "..."]}         -- bullet list
    {"type": "quote", "text": "..."}                -- pull quote

`slug` must be unique and URL-safe -- it's the only lookup key
routes/pages.py uses to resolve /insights/<slug>.
"""

CATEGORIES = [
    "For NRIs",
    "Regulation",
    "Fund Structures",
    "Markets",
]

ARTICLES = [
    {
        "slug": "gift-city-funds-for-nris-new-route-global-investing",
        "title": "GIFT City Funds for NRIs: A New Route to Global Investing",
        "category": "For NRIs",
        "excerpt": "For decades, NRIs wanting global exposure had to open an overseas brokerage account and navigate a different country's tax code. GIFT City funds collapse that into a single, India-regulated product.",
        "read_minutes": 6,
        "published": "2026-08-18",
        "accent": "blue",
        "body": [
            {"type": "p", "text": "Non-resident Indians have always had a strange relationship with global markets. They live and earn abroad, often in dollars, yet the easiest investment products available to them are still denominated in rupees and domiciled in India. Going the other way -- building genuine international diversification -- traditionally meant opening a brokerage account in a foreign jurisdiction, learning that country's tax forms, and hoping the compliance burden stayed manageable across two tax residencies."},
            {"type": "p", "text": "GIFT City's International Financial Services Centre (IFSC) was built to close that gap. It is a specially regulated zone within India -- carved out at Gujarat International Finance Tec-City -- where funds can be structured under a lighter-touch, internationally benchmarked regime overseen by the IFSCA (International Financial Services Centres Authority), rather than the domestic mutual fund rules that apply to the rest of the country."},
            {"type": "h2", "text": "Why this matters for an NRI specifically"},
            {"type": "p", "text": "A fund domiciled in GIFT IFSC can accept subscriptions in US dollars, report NAVs in US dollars, and route capital into US equities, global ETFs, or diversified international portfolios -- all while remaining a product an NRI subscribes to through a regulated Indian entity, with statements and support in a familiar format. There is no need to wire money to a foreign brokerage, no need to file a foreign tax return purely to hold the investment, and no currency-conversion friction every time a statement is generated."},
            {"type": "ul", "points": [
                "Subscriptions and NAVs are quoted in USD, so there's no rupee-conversion noise sitting on top of your actual returns.",
                "The fund itself sits inside an Indian-regulated IFSC, not a foreign jurisdiction you'd need to separately understand.",
                "Entry tickets range from a few hundred dollars for retail feeder funds to six figures for institutional AIFs, so the route isn't reserved for family offices.",
            ]},
            {"type": "h2", "text": "What 'outbound' actually means here"},
            {"type": "p", "text": "In GIFT City terminology, funds are classified by the direction capital flows. Outbound funds take capital sitting in India (or from NRIs) and deploy it into markets outside India -- US tech, global equity indices, international AIFs. Inbound funds do the reverse: they let foreign and NRI capital flow into India through a structure that qualifies for IFSC tax treatment. Most of what NRIs are hearing about lately, including the fund launches you may have seen shared on LinkedIn, sit on the outbound side -- it's the more novel use case, since NRIs have always been able to invest in India directly."},
            {"type": "h2", "text": "The catch worth knowing about"},
            {"type": "p", "text": "GIFT City outbound funds are still a young category. Track records are short, secondary-market liquidity for some structures is thin, and not every fund publishes a daily public NAV -- institutional AIFs, in particular, are only required to share NAV statements privately with unit holders rather than on a public site. None of that makes the route bad; it just means the due-diligence checklist looks different from picking a mainstream mutual fund. Read the offering documents, understand the lock-in (if any), and confirm the specific tax treatment for your country of residence before committing capital."},
        ],
    },
    {
        "slug": "gift-city-complete-guide-for-nris",
        "title": "GIFT City: The Complete Guide for NRIs",
        "category": "For NRIs",
        "excerpt": "What GIFT City actually is, why India built it, and the practical questions an NRI should have answered before wiring the first dollar.",
        "read_minutes": 9,
        "published": "2026-08-05",
        "accent": "indigo",
        "body": [
            {"type": "p", "text": "GIFT City -- short for Gujarat International Finance Tec-City -- is India's first, and so far only, International Financial Services Centre. It's a purpose-built financial district near Gandhinagar, but the geography is almost beside the point. What actually matters is the legal and regulatory wrapper placed around it: a dedicated regulator, a distinct tax regime, and rules deliberately written to look and feel like Singapore, Dubai, or Luxembourg rather than mainland India."},
            {"type": "h2", "text": "Why India built a separate zone instead of just changing the national rules"},
            {"type": "p", "text": "Financial products that compete internationally -- global funds, offshore banking units, aircraft leasing, reinsurance -- need a regulatory speed and flexibility that a large, systemically important domestic market usually can't offer without risking the rest of the financial system. GIFT City lets India experiment with globally competitive rules inside a fenced-off zone, without rewriting SEBI or RBI regulations that apply to everyone else. The result is a jurisdiction that is legally part of India but economically designed to behave like an offshore financial centre -- with one crucial difference: it's fully within Indian sovereign oversight, which is exactly what makes NRIs and Indian regulators alike more comfortable using it than an actual offshore centre."},
            {"type": "h2", "text": "The regulator: IFSCA"},
            {"type": "p", "text": "Rather than splitting oversight across SEBI, IRDAI, RBI and PFRDA the way the rest of India does, GIFT City has a single unified regulator: the International Financial Services Centres Authority (IFSCA). One regulator writing one rulebook for banking, insurance, capital markets and fund management inside the zone is a big part of why fund launches and approvals can move faster there than in the rest of the country."},
            {"type": "h2", "text": "What kinds of funds actually operate there"},
            {"type": "ul", "points": [
                "Retail feeder funds -- open-ended, comparatively low minimum investment (often as low as a few hundred dollars), daily or near-daily USD NAVs, aimed at a broad investor base.",
                "Portfolio Management Services (PMS) -- personalised, higher-ticket portfolios (commonly around $75,000 and up) for investors who want a bespoke mandate rather than a pooled fund.",
                "Category I, II and III Alternative Investment Funds (AIFs) -- institutional vehicles, typically with six-figure minimum tickets and multi-year lock-ins, used for private equity, credit, and long-short strategies.",
            ]},
            {"type": "h2", "text": "The tax pitch, in plain terms"},
            {"type": "p", "text": "Non-resident investors in GIFT City structures can access a 100% capital-gains tax exemption on transfers of specified offshore securities, no GST on fund management fees, and simplified compliance that in many cases doesn't require a PAN. These benefits are anchored in specific provisions of the Indian Income Tax Act -- Section 10(4D) is the one that comes up most often -- and in IFSCA's own fund regulations. None of this replaces proper tax advice in your country of residence, but it does mean the Indian side of the transaction is unusually clean by design."},
            {"type": "h2", "text": "Questions worth asking before you invest"},
            {"type": "ul", "points": [
                "Is this fund outbound (investing abroad) or inbound (investing into India) -- and does that match what you actually want exposure to?",
                "Is the NAV public and how often is it updated -- daily, weekly, or only shared privately with unit holders?",
                "What is the lock-in period, and what are the exit terms if you need liquidity earlier?",
                "Does the fund issue documentation your country's tax authority recognises -- for US-based investors, K-1 versus PFIC treatment is the big one?",
                "Who is the underlying AMC, and is this fund a feeder into a fund they already run elsewhere with a longer track record?",
            ]},
            {"type": "p", "text": "GIFT City isn't a shortcut around due diligence -- it's a better-regulated pipe to run that due diligence through. Treat it that way and it earns the reputation it's building."},
        ],
    },
    {
        "slug": "ifsca-fund-management-regulations-2025-amendments",
        "title": "Amendments to IFSCA Fund Management Regulations 2025: What They Mean for GIFT IFSC",
        "category": "Regulation",
        "excerpt": "IFSCA doesn't sit still. Here's a plain-English walkthrough of why the fund management framework keeps getting amended, and what each round of changes tends to target.",
        "read_minutes": 7,
        "published": "2026-07-22",
        "accent": "emerald",
        "body": [
            {"type": "p", "text": "The IFSCA (Fund Management) Regulations are the single rulebook governing every fund vehicle that operates out of GIFT City -- retail schemes, PMS mandates, and every category of Alternative Investment Fund. Since the framework was first notified, IFSCA has amended it repeatedly, and that's by design: a young jurisdiction competing with Singapore and Dubai for fund managers has to keep the rulebook current with market feedback rather than treating it as fixed for a decade."},
            {"type": "h2", "text": "The recurring themes in recent amendments"},
            {"type": "p", "text": "Reading the last few rounds of changes together, three priorities show up again and again: lowering friction for fund managers who want to relocate or launch in GIFT City, tightening investor-protection and disclosure norms as the fund base grows, and clarifying grey areas that came up in practice once real money started flowing through the structures."},
            {"type": "ul", "points": [
                "Streamlined registration pathways for fund managers already regulated in comparable jurisdictions, so they don't have to rebuild a compliance function from scratch.",
                "Clearer rules on co-investment, side letters, and related-party transactions inside AIFs, closing gaps that were previously handled case-by-case.",
                "Updated minimum-ticket and diversification norms for specific AIF categories, adjusting thresholds as the investor base has broadened.",
                "More explicit disclosure and reporting timelines, bringing GIFT IFSC closer to the reporting cadence investors expect from Luxembourg or Cayman-domiciled funds.",
            ]},
            {"type": "h2", "text": "Why this matters even if you're not a fund manager"},
            {"type": "p", "text": "As an investor, you don't read the regulations directly -- but every launch you see, every new AMC entering GIFT City, and every improvement in reporting quality is downstream of exactly this kind of amendment. A jurisdiction that amends its rulebook often and transparently is, all else equal, a healthier one to have your capital sitting in than one that leaves ambiguity unresolved for years."},
            {"type": "h2", "text": "What to watch for next"},
            {"type": "p", "text": "The direction of travel has been consistently toward harmonising GIFT IFSC's fund rules with global norms -- reporting standards, investor categorisation, and cross-border marketing rules in particular. Expect continued incremental amendments rather than a single sweeping overhaul; that's been the pattern since the framework was first introduced, and there's no sign of it changing."},
        ],
    },
    {
        "slug": "gift-outbound-funds-global-diversification-getting-easier",
        "title": "GIFT Outbound Funds: Why Global Diversification Is Getting Easier for Indian Investors",
        "category": "Markets",
        "excerpt": "A decade ago, an Indian investor wanting US equity exposure had a handful of clunky options. GIFT City's outbound fund ecosystem is quietly turning that into a real, well-regulated menu.",
        "read_minutes": 6,
        "published": "2026-07-10",
        "accent": "orange",
        "body": [
            {"type": "p", "text": "Indian investors have historically under-allocated to international markets -- not out of preference, but because the practical options were limited: a handful of feeder mutual funds subject to the RBI's Liberalised Remittance Scheme headroom, or opening a foreign brokerage account and dealing with two tax systems. GIFT City's outbound fund ecosystem is the first structural attempt to make global diversification a mainstream product rather than a workaround."},
            {"type": "h2", "text": "What's actually changed"},
            {"type": "p", "text": "A growing list of Indian asset management companies -- names that already run large domestic mutual fund businesses -- have set up GIFT IFSC entities specifically to offer outbound share classes. These are frequently structured as feeder funds into an established global strategy the AMC (or a partner) already runs, which means an Indian or NRI investor gets access to a strategy with a genuine multi-year track record, just wrapped in a GIFT City-domiciled, USD-denominated feeder."},
            {"type": "ul", "points": [
                "Lower minimums than a typical international brokerage account or offshore fund would demand.",
                "USD-denominated NAVs, removing a layer of currency bookkeeping from your own portfolio tracking.",
                "A familiar KYC and onboarding process, run through an Indian-regulated distributor rather than a foreign platform.",
                "Regulatory oversight from IFSCA, rather than relying entirely on a foreign jurisdiction's investor-protection regime.",
            ]},
            {"type": "h2", "text": "The strategies on offer are broadening"},
            {"type": "p", "text": "Early outbound launches leaned heavily on US large-cap and Nasdaq-style index exposure -- an easy story to sell and easy to benchmark. The category has since broadened into diversified global equity, sector-specific strategies (financials, healthcare, technology), and increasingly into Category III AIFs running long-short or multi-strategy mandates for investors who want more than a passive index wrapper."},
            {"type": "h2", "text": "What this doesn't solve"},
            {"type": "p", "text": "Outbound funds still ultimately compete with simply opening an international brokerage account for investors who are comfortable doing so -- fees, tracking error versus the underlying strategy, and liquidity terms all deserve scrutiny fund-by-fund. What GIFT City changes is the floor: even an investor who has never dealt with a foreign broker now has a regulated, rupee-adjacent path into the same underlying exposure."},
        ],
    },
    {
        "slug": "outbound-vs-inbound-two-directions-of-capital-flow",
        "title": "Outbound vs Inbound: Understanding the Two Directions of Capital Flow in GIFT City",
        "category": "Fund Structures",
        "excerpt": "Every GIFT City fund points in one of two directions. Knowing which one you're looking at is the fastest way to understand what a fund is actually for.",
        "read_minutes": 5,
        "published": "2026-06-28",
        "accent": "blue",
        "body": [
            {"type": "p", "text": "GIFT City funds are usually described first by strategy -- equity, debt, AIF, PMS -- but the more fundamental split is directional: is the capital flowing out of India into global markets, or into India from foreign and NRI investors? Getting this right before you look at anything else saves a lot of confusion later."},
            {"type": "h2", "text": "Outbound funds"},
            {"type": "p", "text": "Outbound funds take capital that originates in India, or from NRIs anywhere, and deploy it outside India -- into US equities, global indices, or international alternative strategies. The investor is typically Indian or NRI; the underlying exposure is foreign. This is the category behind most of the recent 'invest globally through GIFT City' launches, and the one this site's Outbound Funds page tracks."},
            {"type": "h2", "text": "Inbound funds"},
            {"type": "p", "text": "Inbound funds run the other way: foreign and NRI capital flows through a GIFT IFSC-domiciled structure into Indian securities -- equities, debt, or a blend. For a foreign institutional investor or an NRI who wants exposure to India's growth story, an inbound GIFT City fund offers a cleaner tax and compliance experience than investing directly as a foreign portfolio investor would, since the structure is purpose-built for exactly that use case."},
            {"type": "h2", "text": "Why the distinction changes your due diligence"},
            {"type": "ul", "points": [
                "Outbound funds carry currency and foreign-market risk on top of manager risk -- you're underwriting both the strategy and the market it invests in.",
                "Inbound funds carry India-market risk, but the tax and compliance advantages tend to be the more interesting part of the pitch for a foreign holder.",
                "Regulatory and disclosure norms can differ slightly by direction, since the investor base each is designed for is different.",
                "A fund's name alone doesn't always tell you which direction it runs -- always confirm via the factsheet or offer document rather than assuming.",
            ]},
            {"type": "p", "text": "Neither direction is inherently 'better' -- they solve different problems for different investors. An NRI chasing US equity exposure wants outbound; an NRI who already has that and wants tax-efficient access back into India wants inbound. Some sophisticated investors end up holding both, for exactly opposite reasons."},
        ],
    },
    {
        "slug": "alternative-investment-funds-aifs-gift-city-primer",
        "title": "Alternative Investment Funds (AIFs) in GIFT City: A Primer for Sophisticated Investors",
        "category": "Fund Structures",
        "excerpt": "AIFs are the least visible, highest-minimum corner of the GIFT City fund universe -- and often the one institutional money moves through first.",
        "read_minutes": 7,
        "published": "2026-06-12",
        "accent": "indigo",
        "body": [
            {"type": "p", "text": "If retail feeder funds are GIFT City's public face, Alternative Investment Funds are its institutional backbone. AIFs are pooled vehicles built for sophisticated investors -- family offices, institutions, and high-net-worth individuals -- who can absorb higher minimums and longer lock-ins in exchange for strategies a daily-NAV retail fund simply can't run."},
            {"type": "h2", "text": "The three categories, briefly"},
            {"type": "ul", "points": [
                "Category I: funds with positive economic externalities that regulators want to encourage -- venture capital, infrastructure, and social-impact strategies typically fall here, often with lighter leverage restrictions.",
                "Category II: the largest bucket by assets -- private equity, private credit, and real estate funds that don't take on significant leverage beyond day-to-day operational needs.",
                "Category III: funds that trade more actively and can use leverage and derivatives -- long-short equity, arbitrage, and multi-strategy funds live here.",
            ]},
            {"type": "h2", "text": "Why minimums are so much higher"},
            {"type": "p", "text": "A typical GIFT City AIF sets a minimum ticket in six figures (commonly cited around $150,000), multiple times higher than the retail feeder minimum. That's not arbitrary gatekeeping -- it reflects both regulatory intent (AIFs are meant for investors who can evaluate illiquid, complex strategies without the same protections a retail scheme provides) and practical fund economics, since many AIF strategies simply don't scale efficiently below a certain ticket size."},
            {"type": "h2", "text": "The NAV transparency question"},
            {"type": "p", "text": "One thing that regularly confuses newcomers: many GIFT City AIFs don't publish a public NAV anywhere. That isn't a red flag -- under IFSCA's regulations, private AIFs are not required to disclose NAVs publicly. Instead, capital-call statements, portfolio updates, and NAV figures go directly to registered unit holders, the same way a private equity fund anywhere in the world would report to its LPs. If you're evaluating a GIFT City AIF and can't find a public NAV, that's expected -- ask the fund manager directly instead of treating the absence as a data gap on a tracker site."},
            {"type": "h2", "text": "Lock-ins and liquidity"},
            {"type": "p", "text": "Expect lock-in periods of two to four years depending on strategy, longer for Category I and II funds running genuinely illiquid underlying assets. Category III funds trading liquid instruments sometimes offer more frequent redemption windows, but 'AIF' and 'daily liquidity' rarely belong in the same sentence -- treat any AIF allocation as patient capital by default."},
        ],
    },
    {
        "slug": "retail-feeder-funds-explained-global-markets-from-500",
        "title": "Retail Feeder Funds Explained: How Indians Can Access Global Markets from $500",
        "category": "Fund Structures",
        "excerpt": "The retail feeder fund is GIFT City's most accessible product -- and the one most likely to be the first GIFT City investment most people ever make.",
        "read_minutes": 5,
        "published": "2026-05-30",
        "accent": "emerald",
        "body": [
            {"type": "p", "text": "Of the three broad fund structures operating out of GIFT City -- retail feeder funds, PMS, and AIFs -- the retail feeder fund is the one built for the widest possible investor base. Minimum tickets are frequently as low as a few hundred dollars, the funds are open-ended, and NAVs are published on a regular, often daily, cadence."},
            {"type": "h2", "text": "What 'feeder' actually means"},
            {"type": "p", "text": "A feeder fund doesn't run its own independent strategy from scratch. It pools investor money in GIFT City and 'feeds' it into a master fund -- often a strategy the same AMC already manages in another jurisdiction with a longer track record. You get exposure to that established strategy, denominated in USD, through a GIFT IFSC entity, without needing an account with the master fund's home-jurisdiction platform directly."},
            {"type": "h2", "text": "Why this structure is attractive to AMCs"},
            {"type": "ul", "points": [
                "It lets an AMC extend an existing, proven strategy to Indian and NRI investors without building an entirely new investment process.",
                "It keeps operational complexity low -- the master fund's manager keeps running the same book; GIFT City handles distribution and local compliance.",
                "It gives investors a genuine multi-year track record to evaluate, rather than a brand-new strategy with no history.",
            ]},
            {"type": "h2", "text": "What to check before investing"},
            {"type": "p", "text": "Two numbers matter more than most others when comparing retail feeder funds: the total expense ratio (which stacks the feeder's own costs on top of whatever the master fund already charges) and tracking difference versus the underlying strategy over time. A feeder with a clean, tight tracking history and a reasonable combined expense ratio is doing its job; wide, unexplained divergence from the master fund's reported returns is worth asking the AMC about directly."},
        ],
    },
    {
        "slug": "tax-case-for-gift-city-section-10-4d-churn-tax",
        "title": "The Tax Case for GIFT City: Section 10(4D), Churn Tax, and Why IFSC Matters",
        "category": "Regulation",
        "excerpt": "Tax efficiency is the single biggest reason GIFT City funds exist at all. Here's what the exemptions actually cover, in language that isn't a tax code excerpt.",
        "read_minutes": 6,
        "published": "2026-05-15",
        "accent": "orange",
        "body": [
            {"type": "p", "text": "Strip away the marketing language and GIFT City's core pitch is a tax pitch. If the same fund could be run with identical economics anywhere else, IFSC wouldn't have grown the way it has. Three specific mechanisms do most of the work."},
            {"type": "h2", "text": "Section 10(4D): the capital-gains exemption"},
            {"type": "p", "text": "Section 10(4D) of the Income Tax Act exempts specified income of a Category III AIF (and certain other IFSC-based funds) from tax, where the income arises from the transfer of specified securities, provided the fund satisfies IFSCA's conditions and reports appropriately. In practical terms, this is what lets a non-resident investor's gains inside a compliant GIFT City fund avoid the layer of Indian capital-gains tax that would otherwise apply to a comparable structure outside the IFSC."},
            {"type": "h2", "text": "Churn tax -- and why avoiding it is valuable"},
            {"type": "p", "text": "'Churn tax' is shorthand for the capital-gains tax triggered every time a fund's manager buys and sells securities inside the portfolio -- rebalancing, taking profits, rotating sectors. In a structure where this tax applies, active management has a real, compounding drag: every rebalance costs something before it even has a chance to add value. Funds routed through structures designed to avoid this friction (certain GIFT City structures included) let a manager actually manage the portfolio without a tax penalty attached to every decision."},
            {"type": "h2", "text": "No GST on fund management fees"},
            {"type": "p", "text": "Fund management fees charged from a GIFT IFSC entity to a fund are exempt from GST, unlike the domestic mutual fund industry where GST applies to management fees as a matter of course. For a fund with meaningful assets under management, this isn't a rounding error -- it's a real, structural cost advantage that can show up directly in a lower expense ratio."},
            {"type": "h2", "text": "The honest caveat"},
            {"type": "p", "text": "None of these exemptions are unconditional. They depend on the fund satisfying IFSCA's specific structural and reporting requirements, and on your own country of tax residence not clawing back the benefit through its own rules (foreign tax credit mechanics, controlled-foreign-corporation rules, and PFIC treatment for US persons are the ones that most often complicate the picture). GIFT City makes the Indian side of the tax equation clean; it can't make the other side of your tax residency disappear. Always confirm the full picture with a qualified advisor before assuming a headline exemption applies to you personally."},
        ],
    },
    {
        "slug": "how-to-invest-in-gift-city-funds-as-an-nri-step-by-step",
        "title": "How to Invest in GIFT City Funds as an NRI: A Step-by-Step Guide",
        "category": "For NRIs",
        "excerpt": "The onboarding process is more standardised than most first-time investors expect. Here's what actually happens between deciding to invest and holding your first unit.",
        "read_minutes": 6,
        "published": "2026-04-27",
        "accent": "blue",
        "body": [
            {"type": "p", "text": "Investing in a GIFT City fund as an NRI follows a fairly predictable sequence, whether the fund is a retail feeder, a PMS mandate, or an AIF. The details vary by fund and distributor, but the shape of the process doesn't."},
            {"type": "h2", "text": "1. Confirm eligibility and pick a direction"},
            {"type": "p", "text": "Start by confirming you meet the fund's investor-eligibility criteria -- most retail feeder funds accept NRIs broadly, while PMS and AIF structures may have country-specific restrictions tied to how the fund is marketed. Decide whether you're looking for outbound exposure (global markets) or inbound exposure (India, from abroad) -- this narrows the fund universe immediately."},
            {"type": "h2", "text": "2. Complete KYC through a registered distributor or the AMC directly"},
            {"type": "p", "text": "GIFT City funds are distributed through registered intermediaries or directly by the AMC's IFSC entity. KYC typically requires identity and address proof, an overseas bank account (or NRE/NRO account, depending on the fund's remittance requirements), and standard source-of-funds documentation. This is generally lighter than opening a foreign brokerage account from scratch, since the distributor is operating under Indian-recognised compliance standards."},
            {"type": "h2", "text": "3. Fund the investment"},
            {"type": "p", "text": "Subscriptions are typically funded via wire transfer in USD (or the fund's base currency) from your overseas account, or in some cases through NRE/FCNR route remittances depending on the specific fund's structure and your own banking setup. Confirm the exact remittance instructions with the fund or distributor -- getting reference details wrong is the most common reason NRI subscriptions get delayed."},
            {"type": "h2", "text": "4. Understand what you'll receive back"},
            {"type": "ul", "points": [
                "Retail feeder funds: periodic account statements and, usually, access to a daily or regularly updated NAV.",
                "PMS mandates: a personalised portfolio statement showing individual holdings, since the money isn't pooled the same way a fund is.",
                "AIFs: capital-call notices as the fund draws down committed capital, followed by periodic NAV and portfolio statements sent privately to unit holders.",
            ]},
            {"type": "h2", "text": "5. Plan your exit before you need it"},
            {"type": "p", "text": "Know the redemption terms -- notice period, any exit load, and lock-in expiry if applicable -- before you invest, not when you want your money back. This is standard advice for any fund investment, but it matters more here simply because some GIFT City structures (particularly AIFs) have real, multi-year lock-ins that aren't always obvious from a one-page factsheet."},
        ],
    },
    {
        "slug": "why-global-amcs-are-setting-up-in-gift-city-ifsc",
        "title": "Why Global AMCs Are Setting Up Shop in GIFT City IFSC",
        "category": "Markets",
        "excerpt": "It isn't just Indian fund houses extending their reach abroad -- GIFT City is increasingly a two-way street for asset managers.",
        "read_minutes": 5,
        "published": "2026-04-08",
        "accent": "indigo",
        "body": [
            {"type": "p", "text": "The easy narrative around GIFT City is that Indian AMCs are using it to offer their existing domestic customers a route into global markets. That's true, and it's the biggest visible use case today. But the more interesting long-term story is why asset managers who have nothing to do with India's domestic mutual fund industry are choosing to register an IFSC entity at all."},
            {"type": "h2", "text": "A regulator built to move at fund-industry speed"},
            {"type": "p", "text": "IFSCA was explicitly designed as a single-window regulator for the entire financial services stack inside GIFT City -- fund management, banking, insurance, and capital markets under one authority rather than split across SEBI, RBI, IRDAI, and PFRDA. For a fund manager evaluating where to domicile a new vehicle, a unified, fund-industry-literate regulator that can move quickly is a real competitive factor against incumbents like Singapore, Dubai's DIFC, or Luxembourg."},
            {"type": "h2", "text": "Access to a genuinely large, underserved investor base"},
            {"type": "p", "text": "India's NRI population is enormous, increasingly wealthy, and historically underserved by products denominated in a currency and regulatory language they're comfortable with. A global AMC that sets up a GIFT City feeder gets a distribution channel into that population without needing to build an entirely separate India go-to-market function from scratch -- distribution can run through existing Indian intermediaries already registered to sell IFSC products."},
            {"type": "h2", "text": "Cost and tax structure"},
            {"type": "p", "text": "The same tax mechanics that make GIFT City attractive to investors -- capital-gains exemptions under Section 10(4D), no GST on management fees, simplified compliance -- make it structurally cheaper to run a fund from, all else equal, than many alternative jurisdictions. For a manager choosing where to domicile a new share class purely on cost and regulatory grounds, that's not a small factor."},
            {"type": "h2", "text": "What this means going forward"},
            {"type": "p", "text": "As more global names establish a genuine presence in GIFT City rather than a purely nominal one, the fund menu available to Indian and NRI investors should keep broadening past feeder structures into strategies that simply didn't have a compliant India-adjacent distribution path before. That's the trend worth watching more than any single fund launch."},
        ],
    },
    {
        "slug": "usd-denominated-investing-why-currency-matters-for-nri-portfolios",
        "title": "USD-Denominated Investing: Why Currency Matters for NRI Portfolios",
        "category": "For NRIs",
        "excerpt": "A return figure means something different depending on which currency it's measured in. For NRIs earning and spending in dollars, that difference is not academic.",
        "read_minutes": 5,
        "published": "2026-03-20",
        "accent": "emerald",
        "body": [
            {"type": "p", "text": "An NRI earning a salary in US dollars, paying US dollar expenses, and saving toward US dollar goals (a home purchase, retirement, a child's education abroad) has a currency problem hiding inside almost every rupee-denominated Indian investment: the return that matters to them isn't the rupee return the statement shows -- it's that return adjusted for the rupee's movement against the dollar over the holding period."},
            {"type": "h2", "text": "Why this quietly distorts decision-making"},
            {"type": "p", "text": "The rupee has depreciated against the dollar fairly consistently over long periods, which means a rupee-denominated investment needs to outperform its dollar-denominated benchmark by roughly the depreciation rate just to break even in dollar terms. Investors who only look at the rupee number on their statement can end up feeling good about a return that, translated back into the currency they actually spend, was mediocre or worse."},
            {"type": "h2", "text": "What a USD-denominated GIFT City fund changes"},
            {"type": "ul", "points": [
                "The NAV you see is already in dollars -- no separate mental conversion step, and no currency assumption baked silently into your performance tracking.",
                "Currency risk doesn't disappear, but it becomes explicit and manageable -- you know exactly what's driving your return, rather than blending market performance and currency movement into one confusing number.",
                "For outbound funds investing in dollar-denominated assets, there's no currency mismatch at all between the fund's holdings and its reporting currency.",
            ]},
            {"type": "h2", "text": "This isn't just an NRI-only advantage"},
            {"type": "p", "text": "Resident Indian investors with dollar-denominated future liabilities -- a child heading overseas for university, a planned relocation -- face a version of the same problem and can use the same tools. But it's NRIs, whose day-to-day financial life already runs in a foreign currency, for whom this stops being a minor optimisation and becomes close to a basic requirement for accurate portfolio tracking."},
            {"type": "p", "text": "None of this is a case for abandoning rupee assets -- most NRIs still have real rupee liabilities in India (family support, property, eventual return plans) that justify holding rupee investments too. It's a case for being deliberate about which currency each part of your portfolio is actually denominated in, and choosing products -- GIFT City's USD funds among them -- that match your goals rather than defaulting to whatever's most familiar."},
        ],
    },
    {
        "slug": "gift-city-2026-numbers-behind-indias-financial-hub",
        "title": "GIFT City in 2026: The Numbers Behind India's Fastest-Growing Financial Hub",
        "category": "Markets",
        "excerpt": "A look at how far GIFT City's fund ecosystem has come -- and the trajectory that's driving so many AMCs to launch a presence there now rather than wait.",
        "read_minutes": 6,
        "published": "2026-02-14",
        "accent": "orange",
        "body": [
            {"type": "p", "text": "It's easy to describe GIFT City in purely qualitative terms -- 'India's answer to Singapore,' 'a fenced-off financial free zone' -- without engaging with the more useful question: is the fund ecosystem inside it actually growing, and is that growth broad-based or concentrated in a handful of headline launches?"},
            {"type": "h2", "text": "Breadth over headline numbers"},
            {"type": "p", "text": "The more telling signal than any single AUM figure is breadth: the number of distinct AMCs that have moved from 'exploring GIFT City' to 'operating a live, subscribable fund there' has climbed steadily rather than in one dramatic wave. Retail feeder funds, PMS mandates, and AIFs across all three categories are now represented, which matters more for the ecosystem's durability than concentration in one product type would."},
            {"type": "h2", "text": "Where the growth is actually coming from"},
            {"type": "ul", "points": [
                "Established domestic AMCs extending existing global strategies into GIFT-domiciled feeder share classes for NRI and resident distribution.",
                "New entrants building AIF platforms specifically for GIFT City rather than adapting an existing domestic structure.",
                "A gradual increase in inbound structures, as foreign and NRI capital increasingly uses GIFT IFSC as the preferred route into Indian markets rather than direct foreign-portfolio-investor registration.",
            ]},
            {"type": "h2", "text": "The regulatory tailwind behind it"},
            {"type": "p", "text": "None of this growth happens in a vacuum -- it tracks closely with IFSCA's own pace of rule-making. Each round of amendments to the Fund Management Regulations that lowers friction for new registrations or clarifies a previously ambiguous point tends to be followed by a fresh wave of fund launches, which is itself a reasonably good leading indicator that the regulatory environment is being read as stable and improving rather than static."},
            {"type": "h2", "text": "What would make this durable rather than a moment"},
            {"type": "p", "text": "The honest open question is whether GIFT City becomes a genuine long-term alternative to Singapore or Dubai for fund domicile decisions, or remains primarily a distribution channel Indian AMCs use to reach NRIs. The regulatory groundwork for the former exists; whether global capital treats it that way over the next several years is the thing actually worth watching, more than any individual quarter's launch count."},
        ],
    },
]


def get_article(slug: str):
    """Returns the article dict matching `slug`, or None if no article
    has that slug. Case-sensitive -- slugs are always generated/stored
    lowercase, so callers should not need to normalise case themselves."""
    return next((a for a in ARTICLES if a["slug"] == slug), None)


def related_articles(slug: str, limit: int = 3):
    """Returns up to `limit` other articles, preferring same-category
    matches first so a reader finishes one article and sees relevant
    next reads rather than an arbitrary shuffle."""
    current = get_article(slug)
    others = [a for a in ARTICLES if a["slug"] != slug]
    if current:
        others.sort(key=lambda a: a["category"] != current["category"])
    return others[:limit]

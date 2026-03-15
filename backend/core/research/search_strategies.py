"""
Search strategies for Tavily/Crawl4AI-powered corporate research.
"""

from __future__ import annotations

from datetime import datetime


def promoter_fraud_queries(
    company_name: str,
    promoter_names: list[str],
    gstin: str | None = None,
) -> list[dict]:
    queries: list[dict] = [
        {
            "query": f'"{company_name}" fraud OR scam OR default OR NPA OR insolvency',
            "type": "FRAUD_ALERT",
            "priority": 1,
        },
        {
            "query": f'"{company_name}" ED raid OR CBI OR SFIO OR income tax raid',
            "type": "FRAUD_ALERT",
            "priority": 1,
        },
        {
            "query": f'"{company_name}" GST fraud OR fake invoice OR circular trading',
            "type": "FRAUD_ALERT",
            "priority": 1,
        },
    ]

    for promoter in promoter_names:
        queries.extend(
            [
                {
                    "query": f'"{promoter}" fraud OR arrest OR ED OR CBI OR chargesheet',
                    "type": "PROMOTER_BACKGROUND",
                    "priority": 1,
                },
                {
                    "query": f'"{promoter}" income tax raid OR benami OR PMLA',
                    "type": "PROMOTER_BACKGROUND",
                    "priority": 2,
                },
            ]
        )

    if gstin:
        queries.append(
            {
                "query": f'"{gstin}" GSTIN fake invoice OR ITC fraud',
                "type": "FRAUD_ALERT",
                "priority": 1,
            }
        )

    return queries


def litigation_queries(
    company_name: str,
    promoter_names: list[str],
    cin: str | None = None,
) -> list[dict]:
    queries: list[dict] = [
        {
            "query": f'site:ecourts.gov.in "{company_name}" NCLT OR CIRP OR insolvency OR liquidation',
            "type": "LITIGATION",
            "priority": 1,
        },
        {
            "query": f'site:ecourts.gov.in "{company_name}" DRT OR debt recovery tribunal OR SARFAESI',
            "type": "LITIGATION",
            "priority": 1,
        },
        {
            "query": f'site:ecourts.gov.in "{company_name}"',
            "type": "LITIGATION",
            "priority": 1,
        },
        {
            "query": f'site:ecourts.gov.in "{company_name}" court case OR legal notice OR arbitration',
            "type": "LITIGATION",
            "priority": 2,
        },
    ]

    for promoter in promoter_names:
        queries.append(
            {
                "query": f'site:ecourts.gov.in "{promoter}" court case OR FIR OR conviction',
                "type": "LITIGATION",
                "priority": 2,
            }
        )

    if cin:
        queries.append(
            {
                "query": f'site:ecourts.gov.in "{cin}" NCLT OR winding up',
                "type": "LITIGATION",
                "priority": 2,
            }
        )

    return queries


def regulatory_queries(company_name: str, sector: str) -> list[dict]:
    year = datetime.utcnow().year
    common = [
        {
            "query": f'"{company_name}" RBI OR SEBI OR FSSAI OR regulatory notice',
            "type": "REGULATORY_ACTION",
            "priority": 2,
        },
        {
            "query": f'"{company_name}" blacklisted OR debarred OR licence cancelled',
            "type": "REGULATORY_ACTION",
            "priority": 1,
        },
    ]

    sector_templates = {
        "agri_processing": [
            f"India agri processing sector outlook {year}",
            f"MSP policy impact agri processing India {year}",
            f"FSSAI compliance updates food processing India {year}",
        ],
        "nbfc": [
            f"RBI NBFC regulation update {year}",
            f"NBFC asset quality stress India {year}",
        ],
        "real_estate": [
            f"India real estate debt outlook {year}",
            f"RERA enforcement actions India {year}",
        ],
        "textile": [
            f"India textile margins export outlook {year}",
            f"cotton price volatility India textile {year}",
        ],
    }

    for query in sector_templates.get(
        sector.lower().replace(" ", "_"),
        [f"{sector} India outlook {year} regulation"],
    ):
        common.append(
            {
                "query": query,
                "type": "SECTOR_NEWS",
                "priority": 3,
            }
        )
    return common


def mca_queries(
    company_name: str,
    cin: str | None = None,
    director_names: list[str] | None = None,
) -> list[dict]:
    queries = [
        {
            "query": f'site:mca.gov.in "{company_name}"',
            "type": "MCA_FILING",
            "priority": 1,
        },
        {
            "query": f'site:mca.gov.in "{company_name}" struck off OR dormant OR ROC notice',
            "type": "MCA_FILING",
            "priority": 1,
        },
    ]

    if cin:
        queries.append(
            {
                "query": f'site:mca.gov.in "{cin}" MCA master data OR charges',
                "type": "MCA_FILING",
                "priority": 1,
            }
        )
    for director in director_names or []:
        queries.append(
            {
                "query": f'site:mca.gov.in "{director}" DIN MCA disqualified director',
                "type": "MCA_FILING",
                "priority": 2,
            }
        )
    return queries


def company_news_queries(company_name: str, sector: str) -> list[dict]:
    year = datetime.utcnow().year
    return [
        {
            "query": f'"{company_name}" latest news {year}',
            "type": "COMPANY_NEWS",
            "priority": 3,
        },
        {
            "query": f'"{sector}" India growth outlook {year}',
            "type": "SECTOR_NEWS",
            "priority": 3,
        },
    ]


def get_all_queries(
    company_name: str,
    sector: str,
    promoter_names: list[str],
    cin: str | None = None,
    gstin: str | None = None,
    director_names: list[str] | None = None,
    depth: str = "deep",
) -> list[dict]:
    max_priority = {"shallow": 1, "medium": 2, "deep": 3}.get(depth.lower(), 3)
    queries = (
        promoter_fraud_queries(company_name, promoter_names, gstin)
        + litigation_queries(company_name, promoter_names, cin)
        + regulatory_queries(company_name, sector)
        + mca_queries(company_name, cin, director_names)
        + company_news_queries(company_name, sector)
    )
    filtered = [q for q in queries if q["priority"] <= max_priority]
    return sorted(filtered, key=lambda x: x["priority"])

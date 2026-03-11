from data.models import Company
from data.bucket import assign_employee_bucket, assign_revenue_bucket

VALID_INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Manufacturing", "Retail",
    "Energy", "Transportation", "Telecommunications", "Real Estate",
    "Education", "Agriculture", "Entertainment", "Construction",
    "Professional Services",
]

INDUSTRY_ALIASES: dict[str, str] = {
    "tech": "Technology",
    "software": "Technology",
    "information technology": "Technology",
    "it": "Technology",
    "financial services": "Finance",
    "banking": "Finance",
    "insurance": "Finance",
    "pharma": "Healthcare",
    "pharmaceutical": "Healthcare",
    "biotech": "Healthcare",
    "medical": "Healthcare",
    "automotive": "Manufacturing",
    "industrial": "Manufacturing",
    "ecommerce": "Retail",
    "e-commerce": "Retail",
    "oil": "Energy",
    "oil & gas": "Energy",
    "utilities": "Energy",
    "media": "Entertainment",
    "telecom": "Telecommunications",
    "logistics": "Transportation",
    "shipping": "Transportation",
    "consulting": "Professional Services",
    "legal": "Professional Services",
    "accounting": "Professional Services",
    "property": "Real Estate",
    "farming": "Agriculture",
    "food": "Agriculture",
}

_INDUSTRY_LOOKUP: dict[str, str] = {
    name.lower(): name for name in VALID_INDUSTRIES
}
_INDUSTRY_LOOKUP.update({k.lower(): v for k, v in INDUSTRY_ALIASES.items()})


def normalize_industry(raw: str) -> str:
    return _INDUSTRY_LOOKUP.get(raw.lower().strip(), "Other")


def deduplicate(companies: list[Company]) -> list[Company]:
    by_name: dict[str, Company] = {}
    for c in companies:
        key = c.name.lower().strip()
        if key in by_name:
            existing = by_name[key]
            existing_nulls = sum(1 for v in [existing.employeeCount, existing.revenue] if v is None)
            new_nulls = sum(1 for v in [c.employeeCount, c.revenue] if v is None)
            if new_nulls < existing_nulls:
                by_name[key] = c
        else:
            by_name[key] = c
    return list(by_name.values())


def normalize_companies(companies: list[Company]) -> list[Company]:
    result = []
    for c in companies:
        normalized = c.model_copy(update={
            "industry": normalize_industry(c.industry),
            "employeeBucket": assign_employee_bucket(c.employeeCount),
            "revenueBucket": assign_revenue_bucket(c.revenue),
        })
        # Drop companies missing both employee count and revenue
        if normalized.employeeCount is None and normalized.revenue is None:
            continue
        result.append(normalized)
    return deduplicate(result)

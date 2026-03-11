EMPLOYEE_BUCKETS = [
    (5, "<5"),
    (10, "5-9"),
    (20, "10-19"),
    (50, "20-49"),
    (100, "50-99"),
    (250, "100-249"),
    (500, "250-499"),
    (1000, "500-999"),
    (5000, "1K-4.9K"),
    (10000, "5K-9.9K"),
]

REVENUE_BUCKETS = [
    (1_000_000, "<$1M"),
    (5_000_000, "$1-5M"),
    (10_000_000, "$5-10M"),
    (50_000_000, "$10-50M"),
    (100_000_000, "$50-100M"),
    (500_000_000, "$100-500M"),
    (1_000_000_000, "$500M-1B"),
]


def assign_employee_bucket(count: int | None) -> str | None:
    if count is None:
        return None
    for threshold, label in EMPLOYEE_BUCKETS:
        if count < threshold:
            return label
    return "10K+"


def assign_revenue_bucket(revenue: float | None) -> str | None:
    if revenue is None:
        return None
    for threshold, label in REVENUE_BUCKETS:
        if revenue < threshold:
            return label
    return "$1B+"

from data.bucket import assign_employee_bucket, assign_revenue_bucket


def test_employee_bucket_under_5():
    assert assign_employee_bucket(3) == "<5"


def test_employee_bucket_5_to_9():
    assert assign_employee_bucket(5) == "5-9"
    assert assign_employee_bucket(9) == "5-9"


def test_employee_bucket_10_to_19():
    assert assign_employee_bucket(10) == "10-19"
    assert assign_employee_bucket(19) == "10-19"


def test_employee_bucket_20_to_49():
    assert assign_employee_bucket(20) == "20-49"


def test_employee_bucket_50_to_99():
    assert assign_employee_bucket(50) == "50-99"


def test_employee_bucket_100_to_249():
    assert assign_employee_bucket(100) == "100-249"


def test_employee_bucket_250_to_499():
    assert assign_employee_bucket(250) == "250-499"


def test_employee_bucket_500_to_999():
    assert assign_employee_bucket(500) == "500-999"


def test_employee_bucket_1k_to_4999():
    assert assign_employee_bucket(1000) == "1K-4.9K"
    assert assign_employee_bucket(4999) == "1K-4.9K"


def test_employee_bucket_5k_to_9999():
    assert assign_employee_bucket(5000) == "5K-9.9K"


def test_employee_bucket_10k_plus():
    assert assign_employee_bucket(10000) == "10K+"
    assert assign_employee_bucket(500000) == "10K+"


def test_employee_bucket_none():
    assert assign_employee_bucket(None) is None


def test_revenue_bucket_under_1m():
    assert assign_revenue_bucket(500_000) == "<$1M"


def test_revenue_bucket_1_to_5m():
    assert assign_revenue_bucket(1_000_000) == "$1-5M"
    assert assign_revenue_bucket(4_999_999) == "$1-5M"


def test_revenue_bucket_5_to_10m():
    assert assign_revenue_bucket(5_000_000) == "$5-10M"


def test_revenue_bucket_10_to_50m():
    assert assign_revenue_bucket(10_000_000) == "$10-50M"


def test_revenue_bucket_50_to_100m():
    assert assign_revenue_bucket(50_000_000) == "$50-100M"


def test_revenue_bucket_100_to_500m():
    assert assign_revenue_bucket(100_000_000) == "$100-500M"


def test_revenue_bucket_500m_to_1b():
    assert assign_revenue_bucket(500_000_000) == "$500M-1B"


def test_revenue_bucket_1b_plus():
    assert assign_revenue_bucket(1_000_000_000) == "$1B+"
    assert assign_revenue_bucket(400_000_000_000) == "$1B+"


def test_revenue_bucket_none():
    assert assign_revenue_bucket(None) is None

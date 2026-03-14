import csv
from pathlib import Path
from data.sources.oecd import load_oecd_by_employment, ISIC_TO_LABEL, OECD_SIZE_LABELS


def _write_mock_csv(path: Path, rows: list[dict]) -> None:
    """Write a mock OECD CSV file."""
    fieldnames = ["REF_AREA", "ACTIVITY", "MEASURE", "SIZE_CLASS", "TIME_PERIOD", "OBS_VALUE"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


MOCK_DEU_ROWS = [
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_C", "MEASURE": "ENTR", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "150000"},
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_C", "MEASURE": "EMP", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "500000"},
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_C", "MEASURE": "ENTR", "SIZE_CLASS": "S_GE250", "TIME_PERIOD": "2022", "OBS_VALUE": "2000"},
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_C", "MEASURE": "EMP", "SIZE_CLASS": "S_GE250", "TIME_PERIOD": "2022", "OBS_VALUE": "3000000"},
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_F", "MEASURE": "ENTR", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "300000"},
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_F", "MEASURE": "EMP", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "600000"},
    # Older year — should be ignored when 2022 exists
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_C", "MEASURE": "ENTR", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2021", "OBS_VALUE": "140000"},
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_C", "MEASURE": "EMP", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2021", "OBS_VALUE": "480000"},
    # Total size class — should be skipped
    {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_C", "MEASURE": "ENTR", "SIZE_CLASS": "_T", "TIME_PERIOD": "2022", "OBS_VALUE": "999999"},
]

MOCK_FRA_ROWS = [
    {"REF_AREA": "FRA", "ACTIVITY": "ISIC4_C", "MEASURE": "ENTR", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "100000"},
    {"REF_AREA": "FRA", "ACTIVITY": "ISIC4_C", "MEASURE": "EMP", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "350000"},
]


def test_load_single_country(tmp_path):
    _write_mock_csv(tmp_path / "DEU.csv", MOCK_DEU_ROWS)
    records = load_oecd_by_employment(["DEU"], tmp_path)
    assert len(records) == 3
    mfg_small = next(r for r in records if r.target_value == "1-9" and r.source_value == "Manufacturing")
    assert mfg_small.firms == 150000
    assert mfg_small.employees == 500000
    assert mfg_small.source_dimension == "industry"
    assert mfg_small.target_dimension == "employeeSize"


def test_load_aggregates_across_countries(tmp_path):
    _write_mock_csv(tmp_path / "DEU.csv", MOCK_DEU_ROWS)
    _write_mock_csv(tmp_path / "FRA.csv", MOCK_FRA_ROWS)
    records = load_oecd_by_employment(["DEU", "FRA"], tmp_path)
    mfg_small = next(r for r in records if r.target_value == "1-9" and r.source_value == "Manufacturing")
    assert mfg_small.firms == 250000
    assert mfg_small.employees == 850000


def test_skips_total_size_class(tmp_path):
    _write_mock_csv(tmp_path / "DEU.csv", MOCK_DEU_ROWS)
    records = load_oecd_by_employment(["DEU"], tmp_path)
    assert all(r.target_value != "_T" for r in records)


def test_uses_most_recent_year(tmp_path):
    _write_mock_csv(tmp_path / "DEU.csv", MOCK_DEU_ROWS)
    records = load_oecd_by_employment(["DEU"], tmp_path)
    mfg_small = next(r for r in records if r.target_value == "1-9" and r.source_value == "Manufacturing")
    assert mfg_small.firms == 150000


def test_isic_d_e_merge_into_utilities(tmp_path):
    rows = [
        {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_D", "MEASURE": "ENTR", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "1000"},
        {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_D", "MEASURE": "EMP", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "5000"},
        {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_E", "MEASURE": "ENTR", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "2000"},
        {"REF_AREA": "DEU", "ACTIVITY": "ISIC4_E", "MEASURE": "EMP", "SIZE_CLASS": "S1T9", "TIME_PERIOD": "2022", "OBS_VALUE": "8000"},
    ]
    _write_mock_csv(tmp_path / "DEU.csv", rows)
    records = load_oecd_by_employment(["DEU"], tmp_path)
    assert len(records) == 1
    assert records[0].source_value == "Utilities"
    assert records[0].firms == 3000
    assert records[0].employees == 13000


def test_missing_csv_skipped_gracefully(tmp_path):
    records = load_oecd_by_employment(["XXX"], tmp_path)
    assert records == []


def test_isic_to_label_mapping():
    assert ISIC_TO_LABEL["ISIC4_C"] == "Manufacturing"
    assert ISIC_TO_LABEL["ISIC4_F"] == "Construction"
    assert ISIC_TO_LABEL["ISIC4_D"] == "Utilities"
    assert ISIC_TO_LABEL["ISIC4_E"] == "Utilities"


def test_oecd_size_labels():
    assert OECD_SIZE_LABELS["S1T9"] == "1-9"
    assert OECD_SIZE_LABELS["S_GE250"] == "250+"
    assert len(OECD_SIZE_LABELS) == 5

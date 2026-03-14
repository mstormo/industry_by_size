import json
from data.regions import REGIONS, REGION_GROUPS, get_regions_json


def test_regions_has_us():
    us = next(r for r in REGIONS if r.id == "us")
    assert us.label == "United States"
    assert us.source == "census"
    assert us.has_revenue is True
    assert us.group is None


def test_regions_has_germany():
    de = next(r for r in REGIONS if r.id == "de")
    assert de.label == "Germany"
    assert de.group == "europe"
    assert de.source == "oecd"
    assert de.oecd_codes == ["DEU"]
    assert de.has_revenue is False


def test_europe_aggregate_has_all_member_codes():
    europe = next(r for r in REGIONS if r.id == "europe")
    assert "DEU" in europe.oecd_codes
    assert "FRA" in europe.oecd_codes
    assert "GBR" in europe.oecd_codes
    assert len(europe.oecd_codes) >= 20


def test_all_child_codes_in_parent_aggregate():
    """Every child country's code must appear in its parent aggregate."""
    aggregates = {r.id: r for r in REGIONS if r.group is None and r.oecd_codes}
    children = [r for r in REGIONS if r.group is not None]
    for child in children:
        parent = aggregates.get(child.group)
        if parent:
            for code in child.oecd_codes:
                assert code in parent.oecd_codes, f"{child.id} code {code} not in {parent.id}"


def test_region_groups():
    assert "europe" in REGION_GROUPS
    assert "apac" in REGION_GROUPS
    assert "latam" in REGION_GROUPS
    assert "other_oecd" in REGION_GROUPS


def test_get_regions_json():
    data = json.loads(get_regions_json())
    assert "regions" in data
    assert "groups" in data
    us = next(r for r in data["regions"] if r["id"] == "us")
    assert us["hasRevenue"] is True
    de = next(r for r in data["regions"] if r["id"] == "de")
    assert de["hasRevenue"] is False
    assert de["group"] == "europe"

"""Region hierarchy for multi-region data pipeline."""
import json
from dataclasses import dataclass, field


@dataclass
class Region:
    id: str
    label: str
    source: str  # "census" or "oecd"
    group: str | None = None
    oecd_codes: list[str] = field(default_factory=list)
    has_revenue: bool = False


REGIONS: list[Region] = [
    # United States — uses Census Bureau data (SUSB + ecnsize)
    Region("us", "United States", "census", has_revenue=True),

    # Canada
    Region("canada", "Canada", "oecd", oecd_codes=["CAN"]),

    # Europe (aggregate + individual countries)
    Region("europe", "Europe", "oecd", oecd_codes=[
        "DEU", "FRA", "GBR", "ITA", "ESP", "NLD", "BEL", "AUT", "CHE",
        "SWE", "NOR", "DNK", "FIN", "POL", "CZE", "PRT", "IRL", "GRC",
        "HUN", "SVK", "SVN", "EST", "LVA", "LTU", "LUX", "ISL",
        "ROU", "BGR", "HRV",
    ]),
    Region("de", "Germany", "oecd", group="europe", oecd_codes=["DEU"]),
    Region("fr", "France", "oecd", group="europe", oecd_codes=["FRA"]),
    Region("gb", "United Kingdom", "oecd", group="europe", oecd_codes=["GBR"]),
    Region("it", "Italy", "oecd", group="europe", oecd_codes=["ITA"]),
    Region("es", "Spain", "oecd", group="europe", oecd_codes=["ESP"]),
    Region("nl", "Netherlands", "oecd", group="europe", oecd_codes=["NLD"]),
    Region("be", "Belgium", "oecd", group="europe", oecd_codes=["BEL"]),
    Region("at", "Austria", "oecd", group="europe", oecd_codes=["AUT"]),
    Region("ch", "Switzerland", "oecd", group="europe", oecd_codes=["CHE"]),
    Region("se", "Sweden", "oecd", group="europe", oecd_codes=["SWE"]),
    Region("no", "Norway", "oecd", group="europe", oecd_codes=["NOR"]),
    Region("dk", "Denmark", "oecd", group="europe", oecd_codes=["DNK"]),
    Region("fi", "Finland", "oecd", group="europe", oecd_codes=["FIN"]),
    Region("pl", "Poland", "oecd", group="europe", oecd_codes=["POL"]),
    Region("cz", "Czechia", "oecd", group="europe", oecd_codes=["CZE"]),
    Region("pt", "Portugal", "oecd", group="europe", oecd_codes=["PRT"]),
    Region("ie", "Ireland", "oecd", group="europe", oecd_codes=["IRL"]),
    Region("gr", "Greece", "oecd", group="europe", oecd_codes=["GRC"]),

    # Asia-Pacific
    Region("apac", "Asia-Pacific", "oecd", oecd_codes=["JPN", "KOR", "AUS", "NZL"]),
    Region("jp", "Japan", "oecd", group="apac", oecd_codes=["JPN"]),
    Region("kr", "South Korea", "oecd", group="apac", oecd_codes=["KOR"]),
    Region("au", "Australia", "oecd", group="apac", oecd_codes=["AUS"]),
    Region("nz", "New Zealand", "oecd", group="apac", oecd_codes=["NZL"]),

    # Latin America
    Region("latam", "Latin America", "oecd", oecd_codes=["MEX", "COL", "CHL", "CRI", "BRA"]),
    Region("mx", "Mexico", "oecd", group="latam", oecd_codes=["MEX"]),
    Region("co", "Colombia", "oecd", group="latam", oecd_codes=["COL"]),
    Region("cl", "Chile", "oecd", group="latam", oecd_codes=["CHL"]),
    Region("cr", "Costa Rica", "oecd", group="latam", oecd_codes=["CRI"]),
    Region("br", "Brazil", "oecd", group="latam", oecd_codes=["BRA"]),

    # Other OECD
    Region("other_oecd", "Other OECD", "oecd", oecd_codes=["TUR", "ISR"]),
    Region("tr", "Turkey", "oecd", group="other_oecd", oecd_codes=["TUR"]),
    Region("il", "Israel", "oecd", group="other_oecd", oecd_codes=["ISR"]),
]

REGION_GROUPS: dict[str, str] = {
    "europe": "Europe",
    "apac": "Asia-Pacific",
    "latam": "Latin America",
    "other_oecd": "Other OECD",
}


def get_regions_json(only_ids: set[str] | None = None) -> str:
    """Generate regions.json content for frontend consumption.

    If only_ids is provided, only include regions whose id is in the set.
    """
    filtered = REGIONS if only_ids is None else [r for r in REGIONS if r.id in only_ids]
    regions_list = [
        {
            "id": r.id,
            "label": r.label,
            "group": r.group,
            "hasRevenue": r.has_revenue,
        }
        for r in filtered
    ]
    return json.dumps({
        "regions": regions_list,
        "groups": REGION_GROUPS,
    }, indent=2)

from pydantic import BaseModel


class CensusRecord(BaseModel):
    """A single cell from a Census cross-tabulation."""
    source_dimension: str
    source_value: str
    target_dimension: str
    target_value: str
    firms: int
    employees: int


class SankeyNode(BaseModel):
    id: str
    label: str
    dimension: str


class SankeyLink(BaseModel):
    source: str
    target: str
    firms: int
    employees: int


class SankeyData(BaseModel):
    dimensions: list[str]
    nodes: list[SankeyNode]
    links: list[SankeyLink]
    availablePairs: list[tuple[str, str]]

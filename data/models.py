from pydantic import BaseModel


class Company(BaseModel):
    id: str
    name: str
    industry: str
    employeeCount: int | None
    employeeBucket: str | None
    revenue: float | None
    revenueBucket: str | None
    country: str
    source: str


class SankeyNode(BaseModel):
    id: str
    label: str
    dimension: str


class SankeyLink(BaseModel):
    source: str
    target: str
    value: int


class SankeyData(BaseModel):
    dimensions: list[str]
    nodes: list[SankeyNode]
    links: list[SankeyLink]

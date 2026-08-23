from pydantic import BaseModel, ConfigDict, Field, json_schema

from app.models.base import Quarter

class CompanyCreate(BaseModel):
    name: str
    ticker: str
    cik: str
    sector: str
    industry: str
    fiscal_year_end: Quarter

    model_config = ConfigDict(
        from_attributes=True
    )
    
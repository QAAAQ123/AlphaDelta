from pydantic import BaseModel, ConfigDict, Field, json_schema

class CompanyCreate(BaseModel):
    ticker: str
    name: str
    cik: str
    sector: str
    industry: str

    model_config = ConfigDict(
        from_attributes=True
    )
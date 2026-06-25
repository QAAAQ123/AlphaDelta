from pydantic import BaseModel, ConfigDict, Field
from datetime import date
from app.models.base import FormType, Quarter, AnalysisStatus


class FilingCreate(BaseModel):
    accession_number: str
    form_type: FormType
    filing_date: date
    primary_document: str
    year: int
    quarter: Quarter
    analysis_status: AnalysisStatus = Field(default=AnalysisStatus.NOT_ANALYZED)
    company_id: int

    model_config = ConfigDict(from_attributes=True)

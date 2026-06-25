from sqlalchemy.orm import Session
from app.models import Filing
from app.schemas.filing import FilingCreate


def bulk_create_filings(
    db: Session, filing_creates: list[FilingCreate]
) -> list[Filing]:
    db_objects = [Filing(**data.model_dump()) for data in filing_creates]
    db.add_all(db_objects)
    return db_objects

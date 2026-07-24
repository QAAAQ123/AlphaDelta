from sqlalchemy.orm import Session
from app.models.base import Company
from sqlalchemy import select

from app.schemas.company import CompanyCreate


def get_all_from_company(db: Session) -> list[Company]:
    statement = select(Company)
    return db.execute(statement).scalars().all()

def get_company_by_ticker(db: Session, ticker: str) -> Company | None:
    statement = select(Company).where(Company.ticker == ticker)
    return db.execute(statement).scalars().first()

def create_company(company_create: CompanyCreate) -> Company:
    new_company = Company(
            ticker=company_create.ticker,
            name=company_create.name,
            cik=company_create.cik,
            sector=company_create.sector,
            industry=company_create.industry,
            fiscal_year_end=company_create.fiscal_year_end
    )
    return new_company


    
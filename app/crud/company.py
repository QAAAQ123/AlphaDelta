from sqlite3 import IntegrityError

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.base import Company
from sqlalchemy import select

from app.schemas.company import CompanyCreate


def get_all_from_company(db: Session) -> list[Company]:
    statement = select(Company)
    return db.execute(statement).scalars().all()

def create_company(db: Session, company_create: CompanyCreate) -> Company:
    new_company = Company(
            ticker=company_create.ticker,
            name=company_create.name,
            cik=company_create.cik,
            sector=company_create.sector,
            industry=company_create.industry
    )
    try:
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        return new_company
        
    except IntegrityError as e:
        db.rollback()  
        raise e
        
    except SQLAlchemyError as e:
        db.rollback()
        raise e


    
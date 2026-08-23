from sqlalchemy.orm import Session
from app.schemas import CompanyCreate
from app.models import Company
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

def persist_company(db: Session, company: Company) -> Company:
    """company 테이블에 영속성을 위해 새로운 company 데이터를 저장합니다."""
    try:
        db.add(company)
        db.commit()
        return company
    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise

def build_company_create(ticker: str, company_data: dict, cik_fiscal_dict: dict) -> CompanyCreate:
    """위키 크롤링 데이터와 edgartools 조회 결과를 조합해 CompanyCreate를 생성합니다."""
    return CompanyCreate(
        ticker=ticker,
        name=company_data["company"],
        cik=str(cik_fiscal_dict["cik"]),
        industry=company_data.get("industry", ""),
        sector=company_data.get("subsector", ""),
        fiscal_year_end=cik_fiscal_dict["fiscal_year_end"]
    )
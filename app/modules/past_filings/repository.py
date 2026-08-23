from sqlalchemy.orm import Session
from app.models.base import Filing
from app.schemas import FilingCreate
from app.crud import filing as filing_crud

def get_existing_filings(db: Session, company_id: int) -> list[Filing]:
    """
    특정 기업의 모든 기존 공시를 조회합니다.
    
    Args:
        db: 데이터베이스 세션
        company_id: 기업의 DB ID
        
    Returns:
        Filing 객체 리스트
    """
    return db.query(Filing).filter(Filing.company_id == company_id).all()


def bulk_save_original_filings(db: Session, original_filings: list[FilingCreate]) -> list[Filing]:
    """
    원본 공시들을 일괄 저장합니다 (커밋하지 않음).
    
    Args:
        db: 데이터베이스 세션
        original_filings: FilingCreate 스키마 리스트
        
    Returns:
        생성된 Filing 객체 리스트
    """
    db_originals = filing_crud.bulk_create_filings(db, original_filings)
    return db_originals


def bulk_save_amendment_filings(db: Session, amendment_filings: list[FilingCreate]) -> None:
    """
    수정공시들을 일괄 저장합니다 (커밋하지 않음).
    
    Args:
        db: 데이터베이스 세션
        amendment_filings: 수정공시 FilingCreate 스키마 리스트
    """
    if amendment_filings:
        filing_crud.bulk_create_filings(db, amendment_filings)


def commit_filings(db: Session) -> None:
    """
    모든 공시 변경사항을 커밋합니다.
    
    Args:
        db: 데이터베이스 세션
    """
    db.commit()


def rollback_filings(db: Session) -> None:
    """
    모든 공시 변경사항을 롤백합니다.
    
    Args:
        db: 데이터베이스 세션
    """
    db.rollback()

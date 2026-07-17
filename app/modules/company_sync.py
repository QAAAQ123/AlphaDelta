"""
Nasdaq 100 지수 구성 기업을 위키백과에서 크롤링하고
데이터베이스에 정제하여 영속화하는 동기화 모듈입니다.
"""

import uuid
import pandas as pd
import urllib.request
from loguru import logger
from sqlalchemy.orm import Session
from datetime import datetime
from app.core import _request_id
from app.models.base import Filing, Quarter
from app.schemas import CompanyCreate
from app.crud import company as company_crud
from app.models import Company
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

MONTH_TO_QUARTER = [
    Quarter.Q1, Quarter.Q1, Quarter.Q1,  # 1, 2, 3월
    Quarter.Q2, Quarter.Q2, Quarter.Q2,  # 4, 5, 6월
    Quarter.Q3, Quarter.Q3, Quarter.Q3,  # 7, 8, 9월
    Quarter.Q4, Quarter.Q4, Quarter.Q4   # 10, 11, 12월
]

def sync_nasdaq100_index_companies(db: Session):
    """나스닥 100지수의 종목을 최신 기준으로 동기화합니다."""

    token = _request_id.set(str(uuid.uuid4())[:8])

    try:
        with logger.contextualize(ticker="NASDAQ INDEX"):
            logger.info("나스닥 100 종목 DB 동기화 시작")

            latest_companies = _extract_and_clean_df(_fetch_nasdaq100_via_wikipedia())
            if not latest_companies:
                logger.error("동기화 실패: 최신 데이터를 가져오지 못함")
                return

            existing_companies = company_crud.get_all_from_company(db)
            existing_cik_set = {company.cik for company in existing_companies}
            existing_ticker_set = {company.ticker for company in existing_companies} 

            for company_data in latest_companies:
                ticker = company_data["ticker"]
                
                with logger.contextualize(ticker=ticker):
                    #새로운 종목이 편입되어서 모든 데이터를 새롭게 저장
                    if ticker not in existing_ticker_set:
                        new_company_cik_fiscal_dict = _get_cik_and_fiscal_year_end_via_edgartools(ticker)  

                        if not new_company_cik_fiscal_dict:
                            logger.warning(f"Edgartools에서 CIK,회계연도 종료 분기 조회를 실패하여 건너뜁니다.")
                            continue

                        cik_str = str(new_company_cik_fiscal_dict["cik"])
                        if cik_str in existing_cik_set:
                            logger.info(f"이미 DB에 존재하는 CIK: {cik_str}")
                            continue
                        
                        new_company_dto = _build_company_create(ticker,company_data,new_company_cik_fiscal_dict)
                        new_company_entity = company_crud.create_company(new_company_dto)
                            
                        _persist_company(db, new_company_entity)
                        
    finally:
        _request_id.reset(token)


def _fetch_nasdaq100_via_wikipedia() -> bytes | None:
    """
    위키피디아 나스닥 100 종목을 크롤링해서 bytes 형태의 HTML로 반환하는 함수
    """
    try:
        with logger.contextualize(ticker="NASDAQ INDEX",domain="Company"):
            wikipedia_nasdaq_100_url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            logger.info("나스닥 100 지수 구성 기업 위키피디아 크롤링 시작")
            
            req = urllib.request.Request(
                wikipedia_nasdaq_100_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            return urllib.request.urlopen(req).read()
    except Exception as e:
        logger.warning(f"위키피티아 크롤링 실패 None 리턴: {e}")
        return None

def _extract_and_clean_df(html_content: bytes) -> list[dict]:
    """
    크롤링으로 받아온 나스닥 100 html을
    ['ticker', 'company', 'industry', 'subsector']
    dict 형태로 정리해주는 함수
    """
    try:
        tables = pd.read_html(html_content, match="Ticker")
        if not tables:
            raise ValueError("위키백과에서 구성 종목 테이블을 필터링 실패")

        target_df = tables[0]
        col_mapping = _find_column_mapping(target_df.columns)

        if not all(col_mapping.values()):
            raise KeyError("필요한 컬럼(Ticker, Company, Industry, Subsector) 중 일부를 찾을 수 없음")

        logger.info("나스닥 100 지수 구성 기업 컬럼 탐색 성공. 데이터 가공 시작")

        refined_df = _clean_dataframe(target_df, col_mapping)
        return refined_df.to_dict(orient="records")

    except Exception as e:
        logger.error(f"데이터 fetching/parsing 실패: {e}")
        return []

def _find_column_mapping(original_columns: list) -> dict[str,str | None]:
    """실제 컬럼명을 찾아 매핑(TICKER/SYMBOL, COMPANY/NAME, ICB INDUSTRY/INDUSTRY, ICB SUBSECTOR/SUBSECTOR)"""
    return {
        'ticker': next((c for c in original_columns if 'TICKER' in str(c).upper() or 'SYMBOL' in str(c).upper()), None),
        'company': next((c for c in original_columns if 'COMPANY' in str(c).upper() or 'NAME' in str(c).upper()), None),
        'industry': next((c for c in original_columns if 'ICB INDUSTRY' in str(c).upper() or 'INDUSTRY' in str(c).upper()), None),
        'subsector': next((c for c in original_columns if 'ICB SUBSECTOR' in str(c).upper() or 'SUBSECTOR' in str(c).upper()), None),
    }

def _clean_dataframe(dataframe: pd.DataFrame, column_mapping: dict[str,str]) -> pd.DataFrame:
    """필요한 컬럼만 추출, 컬럼명 재작성,NaN 정제"""
    refined_df = dataframe[list(column_mapping.values())].copy()
    refined_df.columns = list(column_mapping.keys())

    for col in refined_df.columns:
        refined_df[col] = refined_df[col].astype(str).str.strip()

    return refined_df

def _get_cik_and_fiscal_year_end_via_edgartools(ticker: str) -> dict | None:
    """edgartools를 통해 기업의 CIK와 회계연도 종료 분기를 수집합니다."""
    with logger.contextualize(ticker=ticker):
        try:
            company = Company(ticker)
            
            # 10-K 공시 조회
            filings = company.get_filings(form="10-K")
            if not filings:
                logger.info("10-K 보고서를 찾을 수 없습니다.")
                return None
            
            # 분기 추출 역할을 다른 함수에 위임 (SRP 준수)
            quarter_enum = _extract_quarter_from_filing(filings.latest())
            if not quarter_enum:
                logger.info("10-K의 period_of_report를 분석할 수 없습니다.")
                return None

            return {
                "fiscal_year_end": quarter_enum,
                "cik": company.cik
            }
            
        except ValueError:
            logger.warning("ticker에 해당하는 cik와 fiscal year end 찾기 실패")
            return None
    
def _extract_quarter_from_filing(filing: Filing) -> Quarter | None:
    """공시(Filing) 객체에서 보고 기간을 파싱하여 Quarter Enum을 반환합니다."""
    period_str = filing.period_of_report
    if not period_str:
        return None
    
    try:
        period_date = datetime.strptime(period_str, "%Y-%m-%d")
        return MONTH_TO_QUARTER[period_date.month - 1]
    except (ValueError, IndexError):
        return None

def _persist_company(db: Session, company: Company) -> Company:
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

def _build_company_create(ticker: str, company_data: dict, cik_fiscal_dict: dict) -> CompanyCreate:
    """위키 크롤링 데이터와 edgartools 조회 결과를 조합해 CompanyCreate를 생성합니다."""
    return CompanyCreate(
        ticker=ticker,
        name=company_data["company"],
        cik=str(cik_fiscal_dict["cik"]),
        industry=company_data.get("industry", ""),
        sector=company_data.get("subsector", ""),
        fiscal_year_end=cik_fiscal_dict["fiscal_year_end"]
    )


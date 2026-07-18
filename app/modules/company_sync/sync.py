import uuid
from loguru import logger
from sqlalchemy.orm import Session
from app.core import _request_id
from app.crud import company as company_crud

from .extractor import fetch_nasdaq100_via_wikipedia, extract_and_clean_df
from .edgar import get_cik_and_fiscal_year_end_via_edgartools
from .repository import build_company_create, persist_company
"""
Nasdaq 100 지수 구성 기업을 위키백과에서 크롤링하고
데이터베이스에 정제하여 영속화하는 동기화 모듈입니다.
"""

def sync_nasdaq100_index_companies(db: Session):
    """나스닥 100지수의 종목을 최신 기준으로 동기화합니다."""

    token = _request_id.set(str(uuid.uuid4())[:8])

    try:
        with logger.contextualize(ticker="NASDAQ INDEX"):
            logger.info("나스닥 100 종목 DB 동기화 시작")

            latest_companies = extract_and_clean_df(fetch_nasdaq100_via_wikipedia())
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
                        new_company_cik_fiscal_dict = get_cik_and_fiscal_year_end_via_edgartools(ticker)  

                        if not new_company_cik_fiscal_dict:
                            logger.warning(f"Edgartools에서 CIK,회계연도 종료 분기 조회를 실패하여 건너뜁니다.")
                            continue

                        cik_str = str(new_company_cik_fiscal_dict["cik"])
                        if cik_str in existing_cik_set:
                            logger.info(f"이미 DB에 존재하는 CIK: {cik_str}")
                            continue
                        
                        new_company_dto = build_company_create(ticker,company_data,new_company_cik_fiscal_dict)
                        new_company_entity = company_crud.create_company(new_company_dto)
                            
                        persist_company(db, new_company_entity)
                        
    finally:
        _request_id.reset(token)
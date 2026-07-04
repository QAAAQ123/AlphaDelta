import uuid
import pandas as pd
import urllib.request
from loguru import logger
from sqlalchemy.orm import Session
import os
import sys
from app.core import _request_id
from app.models.base import Filing, FormType, Quarter
from app.schemas import CompanyCreate
from app.crud import company as company_crud
from app.models import Company
from edgar import Company as edgar_company
from sqlalchemy import select, exc


current_dir = os.path.dirname(os.path.abspath(__file__))
app_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

def get_nasdaq100_index_companies_via_wikipedia() -> list[str]:
    try:
        with logger.contextualize(ticker="NASDAQ INDEX",domain="Company"):
            wikipedia_nasdaq_100_url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            logger.info("나스닥 100 지수 구성 기업 위키피디아 크롤링 시작")
            
            req = urllib.request.Request(
                wikipedia_nasdaq_100_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            html_content = urllib.request.urlopen(req).read()
            
            try:
                tables = pd.read_html(html_content, match="Ticker")
            except ValueError:
                tables = pd.read_html(html_content, match="Symbol")
                
            if not tables:
                raise ValueError("위키백과에서 구성 종목 테이블을 필터링 실패")
            
            # 3. 매칭된 첫 번째 테이블 선택 후 컬럼 처리
            target_df = tables[0]
            orig_cols = target_df.columns
            
            ticker_col = next((c for c in orig_cols if 'TICKER' in str(c).upper() or 'SYMBOL' in str(c).upper()), None)
            company_col = next((c for c in orig_cols if 'COMPANY' in str(c).upper() or 'NAME' in str(c).upper()), None)
            industry_col = next((c for c in orig_cols if 'ICB INDUSTRY' in str(c).upper() or 'INDUSTRY' in str(c).upper()), None)
            subsector_col = next((c for c in orig_cols if 'ICB SUBSECTOR' in str(c).upper() or 'SUBSECTOR' in str(c).upper()), None)

            if not all([ticker_col, company_col, industry_col, subsector_col]):
                raise KeyError("필요한 컬럼(Ticker, Company, Industry, Subsector) 중 일부를 찾을 수 없음")

            logger.info("나스닥 100 지수 구성 기업 컬럼 탐색 성공. 데이터 가공 시작")

            # 4. 필요한 컬럼만 추출하고 깔끔한 이름으로 리네임
            refined_df = target_df[[ticker_col, company_col, industry_col, subsector_col]].copy()
            refined_df.columns = ['ticker', 'company', 'industry', 'subsector']
            
            # 문자열 데이터 공백 및 특수 가공 처리
            for col in refined_df.columns:
                refined_df[col] = refined_df[col].astype(str).str.strip()

            # 5. 상용 DB 적재나 API 결과 서빙에 용이하도록 딕셔너리 리스트(JSON 형태)로 변환
            return refined_df.to_dict(orient="records")
                
    except Exception as e:
        logger.error(f"데이터 fetching/parsing 실패: {e}")
        return []
    
def get_cik_via_edgartools(ticker: str) -> str:

    with logger.contextualize(ticker=ticker):
        try:
            cik = Company(ticker).cik
            return cik
        except ValueError:
            logger.warning("ticker에 해당하는 cik 찾기 실패")
            return None
            

def sync_nasdaq100_index_companies(db: Session):

    token = _request_id.set(str(uuid.uuid4())[:8])

    try:
        with logger.contextualize(ticker="NASDAQ INDEX"):
            logger.info("나스닥 100 종목 DB 동기화 시작")

            latest_companies = get_nasdaq100_index_companies_via_wikipedia()
            if not latest_companies:
                logger.error("동기화 실패: 최신 데이터를 가져오지 못함")
                return

            existing_companies = company_crud.get_all_from_company(db)
            existing_cik_set = {company.cik for company in existing_companies}
            existing_ticker_set = {company.ticker for company in existing_companies} 

            for company_data in latest_companies:
                ticker = company_data["ticker"]
                
                with logger.contextualize(ticker=ticker):
                    if ticker not in existing_ticker_set:
                        cik = get_cik_via_edgartools(ticker)  

                        if not cik:
                            logger.warning(f"SEC EDGAR에서 CIK 조회를 실패하여 건너뜁니다.")
                            continue

                        cik_str = str(cik)
                        if cik_str in existing_cik_set:
                            logger.info(f"이미 DB에 존재하는 CIK: {cik}")
                            continue

                        new_company = CompanyCreate(
                            ticker = ticker,
                            name = company_data["company"],
                            cik = cik_str,
                            industry = company_data.get("industry",""),
                            sector = company_data.get("subsector","")
                        )
                        try:
                            company_crud.create_company(db, new_company)
                            logger.success(f"새로운 회사 DB 저장 성공")
                        except Exception as e:
                            logger.warning(f"새로운 회사를 DB에 저장할 수 없음: {e}")
                            db.rollback()
    finally:
        _request_id.reset(token)
    
def set_companies_fiscal_year_end(db: Session):
    """
    companies에 회계 종료 분기를 추가적으로 저장하는 함수
    1. campanies 전체 가져오기
    2. filing에서 company_id가 맞는 기업의 10-K의 Quarter 찾기
    SELECT c.id AS company_id, f.quater
    FROM companies c
    INNER JOIN filing f ON c.id = f.company_id
    WHERE f.form_type = '10-K'
    3. company_id에 맞게 quarter 추가(업데이트)
    """

    token = _request_id.set(str(uuid.uuid4())[:8])

    with logger.contextualize(ticker="NASDAQ INDEX",domain="Company"):
        logger.debug("기업 회계 종료 분기 저장 시작")
        
        try:
            companies = db.scalars(select(Company)).all()

            stmt = (
                select(Company.id.label("company_id"), Filing.quarter)
                .join(Filing, Company.id == Filing.company_id)
                .where(Filing.form_type == FormType.REGULAR_10_K.value)
            )
            result = db.execute(stmt).all()

            filing_map = {row.company_id: row.quarter for row in result}

            updated_count = 0
            for company in companies:
                if company.id in filing_map:
                    company.fiscal_year_end = filing_map[company.id]
                    updated_count += 1
                
            if updated_count > 0:
                db.commit()
                logger.info(f"총 {updated_count}개 기업의 분기(Quarter) 정보 추가 완료")
            else:
                logger.warning("업데이트할 일치하는 분기 정보가 없습니다.")

        except exc.SQLAlchemyError as e:
            db.rollback()  # 에러 발생 시 원래 상태로 되돌림
            logger.error(f"데이터베이스 업데이트 중 오류 발생: {str(e)}")
            raise e
        except Exception as e:
            db.rollback()
            logger.error(f"예상치 못한 오류 발생: {str(e)}")
            raise e
        finally:
            _request_id.reset(token)
            db.close()



            



if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core import settings, setup_global_mdc_logging

    setup_global_mdc_logging()
    
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as db:
        set_companies_fiscal_year_end(db)
        #sync_nasdaq100_index_companies(db)
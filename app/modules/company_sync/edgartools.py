from loguru import logger
from edgar import Company
from datetime import datetime
from app.models.base import Filing, Quarter


MONTH_TO_QUARTER = [
    Quarter.Q1, Quarter.Q1, Quarter.Q1,  # 1, 2, 3월
    Quarter.Q2, Quarter.Q2, Quarter.Q2,  # 4, 5, 6월
    Quarter.Q3, Quarter.Q3, Quarter.Q3,  # 7, 8, 9월
    Quarter.Q4, Quarter.Q4, Quarter.Q4   # 10, 11, 12월
]


def get_cik_and_fiscal_year_end_via_edgartools(ticker: str) -> dict | None:
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


from loguru import logger
from edgar import Company
import datetime


def fetch_past_20_quarters_filings_info(cik: str, ticker: str):
    """
    edgartools를 통해 과거 20개 분기 공시 정보를 조회합니다.
    
    Args:
        cik: 기업의 CIK 코드
        ticker: 기업의 Ticker 심볼
        
    Returns:
        과거 20개 분기의 공시 객체 리스트 (수정공시 포함)
        조회 실패 시 빈 리스트 반환
    """
    with logger.contextualize(domain="Filing", ticker=ticker):
        try:
            company = Company(cik)

            # 10-K, 10-Q 모두 조회 (수정공시 포함)
            not_amended_filings = company.get_filings(form=["10-K", "10-Q"], amendments=False).head(20)

            target_periods = {f.period_of_report for f in not_amended_filings}
            amended_filings = [
                f for f in company.get_filings(form=["10-K/A", "10-Q/A"])
                if f.period_of_report in target_periods
            ]
            processed_data = list(not_amended_filings) + amended_filings

            logger.success(
                f"최종 수집 완료: 총 {len(processed_data)}개 (원본 {len(not_amended_filings)}개 + 수정공시 {len(amended_filings)}개)"
            )
            return processed_data
        except Exception as e:
            logger.warning(f"Filing 수집 중 치명적 오류 발생: {e}")
        return []

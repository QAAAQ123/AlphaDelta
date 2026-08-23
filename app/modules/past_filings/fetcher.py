from app.core import logger
from edgar import Company


def fetch_past_20_quarters_filings_info(cik: str):
    """
    edgartools를 통해 과거 20개 분기 공시 정보를 조회합니다.
    
    Args:
        cik: 기업의 CIK 코드
        
    Returns:
        과거 20개 분기의 공시 객체 리스트 (수정공시 포함)
        조회 실패 시 빈 리스트 반환
    """
    try:
        company = Company(cik)

        
        not_amended_filings = company.get_filings(form=["10-K", "10-Q"], amendments=False).head(20)
        all_amended_filings = company.get_filings(form=["10-K/A", "10-Q/A"])

        target_periods = _extract_periods(not_amended_filings)
        amended_filings = _filter_amendments_by_period(all_amended_filings, target_periods)
        processed_data = list(not_amended_filings) + amended_filings

        logger.bind(
            total_count=len(processed_data),
            raw_count=len(not_amended_filings),
            amended_count=len(amended_filings),
        ).success("최종 수집 완료")

        return processed_data
    except Exception:
        logger.exception("Filing 수집 중 치명적 오류 발생")
    return []

def _extract_periods(filings) -> set[str]:
    """공시 리스트에서 report period 집합을 추출합니다."""
    return {f.period_of_report for f in filings}

def _filter_amendments_by_period(amended_filings, target_periods: set[str]) -> list:
    """target_periods기간에 해당하는 수정공시만 필터링합니다"""
    return [f for f in amended_filings if f.period_of_report in target_periods]

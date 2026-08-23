"""
손익계산서 항목 QTD 추출 모듈
- 매출은 손익계산서의 항목이여서 단순 getter를 해주면 QTD 값을 얻을 수 있다
- 단, 10-K의 매출은 1년 매출 전체이기 때문에 (10-K의 매출 - 3개분기의 매출)을 해주어야한다.
"""
from typing import Any
from edgar import Filing,Company

#1. get_revenue_qtd
#2. _get_revenue_from_edgartools
#3. _get_revenue_qtd_from_10_k
#4. _get_prior_three_10_q_filings
#5. _deduplicate_by_period
#6. _get_last_3_periods
#7. _extract_revenues_from_filings
#8. _calc_10_k_revenue_qtd

def get_revenue_qtd(filing: Filing) -> int | float | None:
    """
    정기 공시(10-Q, 10-K)에서 매출의 QTD 값을 추출
    ##### Args:
        filing: edagrtools Filing 객체
    ##### Returns:
        revenue: 
            회사마다 반환 타입이 다름(int or float)
            예외 발생시 또는 데이터 없을 시 None
    ##### Raises:
        Exception: edgartools get_revenue() 호출 중 예상치 못한 에러 발생 시
    """
    if filing is None:
        return None

    if filing.form in ("10-Q", "10-Q/A"):
        return _get_revenue_from_edgartools (filing.obj().financials)
    elif filing.form in ("10-K", "10-K/A"):
        return _get_revenue_qtd_from_10_k(filing)

    return None

def _get_revenue_from_edgartools(financials: Any) -> int | float | None:
    """
    10-Q의 매출을 edgartools 단순 get_revenue() 요청
    ##### Args:
        financials: Filing.obj().financials
    ##### Returns:
        revenue:
            회사마다 반환 타입이 다름(int or float)
            예외 발생시 또는 데이터 없을 시 None
    ##### Raises:
        Exception: edgartools get_revenue() 호출 중 예상치 못한 에러 발생 시
    """
    if financials is None:
        return None

    try:
        revenue = financials.get_revenue()
    except AttributeError:
        return None
    except Exception as e:
        raise RuntimeError(f"Edgartools get_revenue() 요청 중 알수 없는 문제 발생: {e}")

    if revenue is None or not isinstance(revenue, (int, float)):
        return None

    return revenue

def _get_revenue_qtd_from_10_k(filing: Filing) -> int | float | None:
    """
    FY인 10-K의 매출을 FY - (1Q,2Q,3Q)하여 4Q의 QTD를 추출
    ##### Args:
        filing: edagrtools Filing 객체
    ##### Returns:
        revenue:
            회사마다 반환 타입이 다름(int or float)
            예외 발생시 또는 데이터 없을 시 None
    ##### Raises:
        Exception: edgartools get_revenue() 호출 중 예상치 못한 에러 발생 시
    """
    ytd_revenue = _get_revenue_from_edgartools(filing.obj().financials)

    if ytd_revenue is None:
        return None
    
    try:
        company = filing.company
        #filing_date의 타입은 str(YYYY-mm-dd)
        filing_date = filing.filing_date
    except AttributeError:
        return None
    except Exception as e:
        raise RuntimeError(f"Edgartools 요청 중 알 수 없는 문제 발생: {e}") from e

    q1_q2_q3_filings = _get_prior_three_10_q_filings(company, filing_date)

    if q1_q2_q3_filings is None:
        return None

    q1_q2_q3_revenues = _extract_revenues_from_filings(q1_q2_q3_filings)
    return _calc_10_k_revenue_qtd(ytd_revenue, q1_q2_q3_revenues)
    

        
def _get_prior_three_10_q_filings(company: Company, filing_date: str) -> list[Filing]:
    """
    대상 10-K와 같은 회계 년도의 10-Q(3개)를 찾아 10-Q list를 리턴
    ##### Args:
            compay: edagrtools Company 객체
            filing_date: 공시 제출일(period_of_report와 대략 3개월 차이)
    ##### Returns:
        - 10-K와 같은 회계연도 종료일을 공유하는 3개의 10-Q(/A) Filing list
        - 3개가 아니면 None return
    ##### Raises:
        Exception: edgartools 호출 중 예상치 못한 에러 발생 시
    """
    try:
        candidate_filings = company.get_filings(
            form="10-Q", amendments=True
        ).filter(date=f":{filing_date}").latest(8)
    except Exception as e:
        raise RuntimeError(f"Edgartools 요청 중 알 수 없는 문제 발생: {e}") from e

    by_period = _deduplicate_by_period(candidate_filings)
    return _get_last_3_periods(by_period)

def _deduplicate_by_period(candidate_filings: list[Filing]) -> dict[str, Filing]:
    """
    같은 period_of_report에 대한 수정본이 존재할 경우 /A의 공시 정보로 덮어 씌움
    ##### Args:
        candidate_filings: 10-K 공시 제출일 기준으로 최신 10-Q,10-Q/A Filing 객체 list
    ##### Returns
        by_period: 같은 period_of_report에 대해 수정본(/A)이 존재할 경우, 원본 대신 수정본을 덮어 씌운 {period_of_date:Filing} 딕셔너리
    ##### Raise:

    """
    if not candidate_filings: #if len(candidate_filings) == 0
        return {}

    by_period = {}
    for f in candidate_filings:
        key = f.period_of_report
        if key not in by_period or f.form.endswith("/A"):
            by_period[key] = f

    return by_period

def _get_last_3_periods(by_period: dict[str, Filing]) -> list[Filing] | None:
    """
    인자로 들어온 dict에서 가장 최신 공시 3개만 뽑음
    ##### Args:
        by_period: {period_of_date:Filing} 딕셔너리
    ##### Returns:
        - 최신 공시 3개 Filing list return
        - 최신 공시가 3개 미만이면 None return
    ##### Raise:

    """
    sorted_periods = sorted(by_period.keys())
    
    if len(sorted_periods) < 3:
        return None

    last_three_filings = sorted_periods[-3:]
    return [by_period[p] for p in last_three_filings]

def _extract_revenues_from_filings(filings: list[Filing]) -> list[int | float | None]:
    """
    각 10-Q Filing에서 revenue를 추출
    """
    return [
        _get_revenue_from_edgartools(f.obj().financials)
        for f in filings
    ]
    
def _calc_10_k_revenue_qtd(ytd_revenue: int | float, q1_q2_q3_revenues: list[int | float]) -> int | float | None:
    """
    10-K의 YTD 매출에서 직전 3개 분기 매출 합을 빼서 Q4 QTD 계산
    ##### Args:
        ytd_revenue: 10-K에서 추출한 연간(FY) 매출
        q1_q2_q3_revenues: 직전 3개 분기의 매출 값 list
    ##### Returns:
        Q4 QTD 매출. q1_q2_q3_revenues 중 None이 있거나 개수가 3개가 아니면 None
    """
    if len(q1_q2_q3_revenues) != 3:
        return None

    if any(r is None for r in q1_q2_q3_revenues):
        return None

    return ytd_revenue - sum(q1_q2_q3_revenues)
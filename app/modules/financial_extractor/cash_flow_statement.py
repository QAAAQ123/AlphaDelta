"""
운영현금흐름(OCF) QTD 계산 
- OCF는 Cash flow statement의 항목이여서 YTD이다.
- YTD이기 때문에, 현재 분기 OCF - 직전 분기 OCF를 해주면 QTD를 얻을 수 있다.
#### 예시
가정: 4분기에 회계년도 종료인 회사
1분기: OCF 그대로
2분기: 2분기 OCF - 1분기 OCF
3분기: 3분기 OCF - 2분기 OCF
4분기: 1년 OCF - 1,2,3분기 OCF
"""

from typing import Callable
from edgar import Financials, Filing, Company
#from edgar import ValidationError
from app.core import logger
from app.models import Quarter

# def get_items_qtd_cash_flow_statement(current_filing: Filing, concept_getters: dict) -> dict:
#     """
#     현금흐름표의 재무 항목들을 YTD -> QTD로 변환
#     ### Args:
#         - filing: 재무 정보를 가져올 정기 및 수정 공시(10-Q(/A), 10-K(/A))
#         - conecpt: 원하는 재무 컨셉(예: ["operating_cash_flow", "free_cash_flow"])
#         - getters: 각 concept에 대응하는 람다 함수 리스트 
#                  (각 함수는 TenQ -> float 서명)
#                  concepts와 getters의 순서는 일치해야 함
#     ### Returns:
#         dict: {"quarter": str, "values": {"concept1": float, "concept2": float}}
#     ### Raises:
#         xxxx
#     ### Example:
#         result = get_items_qtd_cash_flow_statement(
#             target_filing,
#             ["operating_cash_flow", "free_cash_flow"],
#             [lambda f: f.get_operating_cash_flow(), lambda f: f.get_free_cash_flow()]
#         )
#     """
QUARTER_MONTH_DIFF_MAP = {
    9: Quarter.Q1,
    6: Quarter.Q2,
    3: Quarter.Q3,
}

PRIOR_QUARTER_OFFSET = 3

def _convert_to_qtd(
        current_financials: Financials, 
        prior_financials: Financials | None, 
        current_quarter: Quarter, 
        getter: Callable[[Financials], int | float | None]
    ) -> int | float | None:
    """
    책임: 현재,이전 financials의 YTD를 QTD로 변환
    ### Args: 
        - current_financials: 현재 분기 financials
        - prior_financials: 전분기 financials
        - current_quarter: 분기 정보
        - getter: financials.getter()를 호출하는 람다 일급객체
    ### Returns:
        QTD
        - int or float: QTD로 변환된 값
        - None: 현재 분기 or 과거 분기의 YTD가 없을 때
    ### Raise:
        - RuntimeError: getter 호출 중 예상치 못한 오류 발생 시
        (edgartools 내부 오류, 잘못된 financials 구조 등)
    """
    try:
        current_ytd = getter(current_financials)
    except Exception as e:
        raise RuntimeError(f"Edgartools 요청 중 예상하지 못한 문제 발생: {e}") from e

    if current_ytd is None:
        return None

    # 1Q일 때 직전 분기 financials가 있으면 안됨
    if current_quarter == Quarter.Q1:
        if prior_financials is not None:
                logger.bind(prior_financials=type(prior_financials)).warning("Q1 QTD의 직전분기(Q4) 재무 정보가 존재")
        return current_ytd

    try:
        prior_ytd = getter(prior_financials)
    except Exception as e:
            raise RuntimeError(f"Edgartools 요청 중 예상하지 못한 문제 발생: {e}") from e

    #current_ytd는 있는데, prior_ytd가 없는 경우
    if prior_ytd is None:
        logger.warning("직전 분기 YTD가 없어 QTD 계산 불가")
        return None

    return current_ytd - prior_ytd


def _determine_quarter(filing: Filing) -> Quarter | None:
    """
    책임: 공시(Filing) 객체에서 데이터 추출 후 분기 결정 함수 호출
    ### Args:
        - filing (Filing): 대상 SEC 공시 객체
    ### Returns:
        - Quarter: 판별된 Quarter Enum 값
        - None: 조회 실패 및 데이터 불일치 시 
    """
    try:
        form = filing.form
        if form is None:
            logger.bind(form=form).warning("form 없음")
            return None

        fiscal_year_end = filing.company.fiscal_year_end
        if fiscal_year_end is None:
            logger.bind(fiscal_year_end=fiscal_year_end).warning("fiscal_year_end 없음")
            return None

        period_of_report = filing.period_of_report
        if period_of_report is None:
            logger.bind(period_of_report=period_of_report).warning("period_of_report 없음")
            return None
    except Exception as e:
        logger.bind(error=str(e)).warning("Edgartools 호출 중 예상하지 못한 에러 발생")
        return None

    return _determine_quarter_from_months(form, fiscal_year_end, period_of_report)

def _find_prior_period_filing(current_filing: Filing, current_filing_report_month: int) -> Filing | None:
    """
    책임: 직전분기 최신 공시 찾는 함수 조합
    ### Args: 
        current_filing: 현재 공시
        current_filing_report_month: 현재 공시 period_of_report의 month
    ### Returns:
        prior_filing: 직전 분기 공시 중 가장 최근에 제출한 공시
        None: 값이 없거나 에러 발생
    """

    candidate_filings = _find_prior_filing_candidates(current_filing.company, current_filing.filing_date)
    if not candidate_filings: #None or empty list
        return None
    
    filtered_filings = _filter_candidate_filings_by_quarter_offset(candidate_filings, current_filing_report_month)
    if not filtered_filings:
        return None

    return _select_most_recent_filing(filtered_filings)

# 헬퍼의 헬퍼----------------------------------------------------------------------------------------------------------------------

def _determine_quarter_from_months(form: str | None, fiscal_year_end: str | None, period_of_report: str | None) -> Quarter | None:
    """
    책임: 분기 결정
    ### Args:
        - form: 공시 타입
        - fiscal_year_end: 회계년도 종료일
        - period_of_report: 공시 마감월
    ### Returns: 
        - Quarter: 판별된 Quarter Enum 값
        - None: 조회 실패 및 데이터 불일치 시 
    """

    # 10-K는 항상 4Q
    if form in ("10-K", "10-K/A"):
        return Quarter.Q4

    fiscal_end_month = _extract_month(fiscal_year_end,"fiscal_year_end")
    report_month = _extract_month(period_of_report, "period_of_report")

    if fiscal_end_month is None or report_month is None:
        return None

    #회계연도 종료 월과 보고서 마감 월의 차이 mod 연산
    month_diff = (fiscal_end_month - report_month) % 12

    #분기 매핑
    if month_diff in QUARTER_MONTH_DIFF_MAP:
        return QUARTER_MONTH_DIFF_MAP[month_diff]

    logger.bind(
        form=form,
        month_diff=month_diff,
        fiscal_end_month=fiscal_end_month,
        report_month=report_month
    ).warning("분기 결정 실패")
    # 원인 불명확-신뢰할 수 없는 데이터로 취급
    return None 


def _extract_month(date_str: str | None, value_name: str) -> int | None:
    """
    책임: 날짜 문자열에서 월 추출 및 검증
    ### Args:
        - date_str: 파싱할 날짜 문자열
        - value_name: 날짜의 값 이름
    ### Returns: 
        - int: 1-12의 정상적인 월 값
        - None: 파싱 실패 및 데이터 불일치 시 
    """
    if date_str is None:
        logger.bind(value_name=value_name).warning("값 없음")
        return None

    if value_name == "fiscal_year_end": # MMDD
        start, end = 0, 2
        expected_length = 4
    elif value_name == "period_of_report": # YYYY-MM-DD
        start, end = 5, 7
        expected_length = 10
    else:
        logger.bind(value_name=value_name).warning("알 수 없는 value_name")
        return None

    if len(date_str) != expected_length:
        logger.bind(value_name=value_name, date=date_str).warning("비정상적인 date_str 길이")
        return None

    try:
        month = int(date_str[start:end])
    except (ValueError, TypeError, IndexError) as e:
        logger.bind(value_name=value_name,date=date_str, error=str(e)).warning("파싱 실패")
        return None

    if not (1 <= month <= 12):
        logger.bind(value_name=value_name, month=month).warning("비정상적인 month 값")
        return None

    return month
             

def _find_prior_filing_candidates(company: Company, filing_date: str) -> list[Filing] | None:
    """
    책임: 이전 공시 후보 목록 찾기
    ### Args:
        - company: 공시를 제출한 회사
        - filing_date: 공시 제출일
    ### Returns:
        - list[Filing]: 후보 공시 목록
        - None: 조회 실패
    """
    if company is None or filing_date is None:
        return None

    # 후보 fiilng 찾기
    try:
        # list(): n>1일 때 latest()가 EntityFilings를 반환하므로 list[Filing]로 정규화
        # latest()는 index0에 최신 공시로 시작해서 index가 커질 수록 과거 공시
        candidate_filing = list(company.get_filings(
            form="10-Q", 
            amendments=True,
            filing_date=f":{filing_date}" 
        ).latest(6))
        #10-Q는 분기마다 제출되므로 직전분기 공시는 보통 최근 공시에 있음
        #수정 공시는 원본 공시 이후 상당한 기간이 지나 제출될 수 있음
        #6개를 조회하면 현재/직전/전전 + 수정 공시를 충분히 확보 가능

        return candidate_filing
    except Exception as e: # get_filings에서 except로 InvalidDateError를 잡고 있음(프로젝트 edgartools 버전에는 없음)
        logger.bind(error=str(e)).warning("Edgartools 호출 중 예상하지 못한 에러 발생-이전 공시 후보 목록 찾기")
        return None

def _filter_candidate_filings_by_quarter_offset(candidate_filings: list[Filing], current_month: int) -> list[Filing] | None:
    """
    책임: 후보 공시 중 마감일이 직전 분기인 공시만 필터링
    ### Args:
        - candidate_filings: 후보 공시 리스트
        - current_month: 현재 공시의 보고 기간 기준월
    ### Returns:
        - list[Filing]: 직전 분기의 보고 기준월인 공시 목록
            - 조건을 만족하는 공시가 없으면 빈(empty) list를 return
        - None: 필터링 실패
    """
    if current_month is None:
        return None
        
    matching_filing = []
    for f in candidate_filings:
        candidate_month = _extract_month(f.period_of_report, "period_of_report")

        if candidate_month is None:
            logger.bind(period_of_report=f.period_of_report
                        ).warning("period_of_report에서 month 추출 실패, 후보에서 제외")
            continue

        offset = (current_month - candidate_month) % 12

        #한계: 회계연도를 바꾼 해 => 분기 간격이 일시적으로 달라질 수 있음
        if offset == PRIOR_QUARTER_OFFSET:
            matching_filing.append(f)

    return matching_filing


def _select_most_recent_filing(filtered_candidate_filings: list[Filing]) -> Filing | None:
    """
    책임: 직전 분기 공시 목록 중에서 가장 최신에 제출된 공시 선택
    ### Args:
        - filtered_candidate_filings: 직전 분기 공시 목록
    ### Returns:
        - prior_filing: 직전분기 공시들 중 가장 최신에 제출된 공시
        - None: 선택 실패
    """
    if not filtered_candidate_filings:
        return None

    most_recent_date = filtered_candidate_filings[0].filing_date
    most_recent_filing = filtered_candidate_filings[0]
    for f in filtered_candidate_filings[1:]:
        filing_date = f.filing_date
        #str이지만 YYYY-mm-dd format이기 때문에 비교 가능
        #YYYY-mm-dd 형식이 아니면 조용한 실패 -> 단위 테스트 검증
        # >=를 사용하지 않은 이유: latest()가 index 0=최신 순으로 정렬해 반환하므로
        # 동일한 filing_date가 있을 경우 정렬 순서에 의존하지 않고 먼저 발견된 원소를 유지하기 위함
        if filing_date > most_recent_date: 
            most_recent_date = filing_date
            most_recent_filing = f

    return most_recent_filing

        

"""
순 차입금 변동 QTD 계산 모듈
- 순 차입금 변동은 Cash flow statement의 항목이여서 YTD이다.
- YTD이기 때문에, 현재 분기 순 차입금 변동 - 직전 분기 순 차입금 변동를 해주면 QTD를 얻을 수 있다.
- 차입금은 LongTermDebtNoncurrent와 ShortTermBorrowings의 합이다.
short_term = xbrl.query().by_concept("us-gaap:ShortTermBorrowings").to_dataframe()
long_term = xbrl.query().by_concept("us-gaap:LongTermDebtNoncurrent").to_dataframe()
net_borrowing = short_term + long_term
return net_borrowing.iloc[-1] - net_borrowing.iloc[-2]
"""
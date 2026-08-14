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
from edgar import Financials, Filing
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
                logger.bind(type(prior_financials)).warning("Q1 QTD prior_financials가 존재")
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
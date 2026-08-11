"""
손익계산서 항목 QTD 추출 모듈
1. Revenue QTD: get_revenue_qtd
- 매출은 손익계산서의 항목이여서 단순 getter를 해주면 QTD 값을 얻을 수 있다
- 단, 10-K의 매출은 1년 매출 전체이기 때문에 (10-K의 매출 - 3개분기의 매출)을 해주어야한다.
"""
from typing import Any
from edgar import Filing

def _get_revenue_qtd_from_10_q(financials: Any) -> int | float | None:
    """
    10-Q의 매출을 edgartools 단순 get_revenue()로 가져오는 함수
    Args:
        financials: Filing.obj().financials
    Returns:
        revenue:
            회사마다 반환 타입이 다름(int or float)
            예외 발생시 또는 데이터 없을 시 None
    Raises:
        Exception: edgartools get_revenue() 호출 중 예상치 못한 에러 발생 시
    """
    if financials is None:
        return None

    try:
        revenue = financials.get_revenue()
    except AttributeError:
        return None
    except Exception as e:
        raise Exception(f"Edgartools get_revenue() 요청 중 알수 없는 문제 발생: {e}")

    if revenue is None or not isinstance(revenue, (int, float)):
        return None

    return revenue


def get_revenue_qtd(filing: Filing) -> int | float | None:
    """
    정기 공시(10-Q, 10-K)에서 매출의 QTD 값을 추출하는 함수
    Args:
        filing: edagrtools Filing 객체
    Returns:
        revenue: 회사마다 반환 타입이 다름(int or float)
    Raises:
    """
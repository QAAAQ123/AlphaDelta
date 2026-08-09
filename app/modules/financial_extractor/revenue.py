"""
매출(revenue or net income) QTD 계산 모듈
- 매출은 손익계산서의 항목이여서 단순 getter를 해주면 QTD 값을 얻을 수 있다.
Edgartools
1순위-표준화 컨셉. result = self._get_standardized_concept_by_xbrl('income',['Contract Revenue', 'Revenue'],period_offset)
Fallback-라벨 기반 검색. self._get_standardized_concept_value('income', patterns, period_offset)
=> 여기서 메타 데이터(dataframe의 header)의 최신 날짜이면서 days가 짧은 순으로 정렬한다.
예시: 티커-O (리얼리티 인컴)
- 1Q: Three months ended(당년도,직전년도)
- 2Q: Three months ended(당년도,직전년도)와 Six months ended(당년도,직전년도)
- 3Q: Three months ended(당년도,직전년도)와 Nine months ended(당년도,직전년도)
- 4Q(10-K): Years ended(당년도,직전년도,전전년도)
"""
from edgar import Filing
import pandas as pd

def get_revenue_qtd():
    """filing에서 매출(Revenue) QTD 값을 추출하고, 해당 값이 실제 QTD(120일 이하)인지 검증합니다."""
    pass

def _get_income_statement(filing: Filing) -> pd.DataFrame| None:
    """
    책임1. Filing 객체에서 손익계산서를 추출 및 Dataframe으로 render
    Args:
        filing: edgartools Filing 타입
    Returns:
        pd.DataFrame: IS가 있는 경우
        None: IS가 없는 경우
    Raises:
        주요 Error 없음
    """

    financials = filing.obj().financials
     
    if financials is None:
        return None
     
    income_statement = financials.income_statement()
    return income_statement.render(standard=True).to_dataframe()

def _extract_primary_period_meta_data():
     pass
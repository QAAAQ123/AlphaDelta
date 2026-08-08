"""
매출(revenue or net income) QTD 계산 모듈
- 매출은 손익계산서의 항목이여서 단순 getter를 해주면 QTD 값을 얻을 수 있다.
- 하지만 QTD를 모든 회사가 보장 해주는 것이 아니기 때문에 QTD인지 xbrl.reporting_periods로 확인이 필요하다.
- xbrl.reporting_periods가 3개월이 아니라면 QTD 값을 계산해주는 함수를 만들어야 한다.

get_revenue는 QTD,YTD를 알려주지 않고 가장 days가 적은 값을 반환한다. => revenue의 QTD만 계산해주려면 get_revenue_qtd 함수를 만들어야 한다.
get_revenue_qtd(Filings):


_determain_period_kind(Filing):
1. filing에서 xbrl 객체를 추출하고 보고 종료일(period_of_report)을 가져온다.
2. xbrl.reporting_periods 중 type이 "duration"이고 end_date가 보고 종료일과
    일치하는 period들을 필터링한다.
3. 필터링된 period 중 days가 가장 작은 period를 현재 기간으로 선택한다.
4. days <= QUARTER_MAX_DAYS이면 단일 분기(QTD)로 판단하여 "QTD"를 반환한다.
5. days <= YTD_6M_MAX_DAYS이면 "YTD6"(반기)판단하여 "YTD6"를 반환한다.
6. days <= 285 "YTD9"(9개월)판단하여 "YTD9"를 반환한다.
6. 위 조건에 해당하지 않으면 fiscal_period 값을 그대로 반환하고,
    fiscal_period가 없으면 "unknown"을 반환한다.
"""
from edgar import Filing
from app.core import logger

# edgartools 소스와 동일한 상수
QUARTER_MAX_DAYS = 120
YTD_6M_MAX_DAYS = 229
YTD_9M_MAX_DAYS = 329



def get_revenue_qtd(filing: Filing):
    """
    매출의 QTD를 return한다.

    Args:
    filing (Filing): Edgartools Filing 타입

    Returns:
    int | float | None: 공시마다 달라짐
    edgartools 소스코드: return float(value) if '.' in str(value) else int(value)- edgartools/edgar/financials.py 라인 424,250
    - int: 공시의 반환값이 int인 경우
    - float: 공시의 반환값에 소수점이 있는 경우
    - None: 매출 QTD가 없는 경우
    Raises:
    """
    with logger.contextualize(domain = "Finance", job = "매출 QTD 추출", accession_number = filing.accession_no):
        period_kind = _determine_period_kind(filing)
        logger.info("매출 QTD 추출 시작", period_kind=period_kind)

        revenue = _extract_revenue_by_period(filing, period_kind)
        logger.info("매출 추출 완료", revenue=revenue)
        return revenue


def _determine_period_kind(filing:Filing) -> str:
    """
    기간의 종류(QTD,YTD)를 결정한다.
    
    Args:
        filing (Filing): Edgartools Filing 타입

    Returns:
        str: 기간 종류
            - "QTD": days <= QUARTER_MAX_DAYS
            - "YTD6": days <= YTD_6M_MAX_DAYS
            - "YTD9": days <= YTD_9M_MAX_DAYS
            - "unknown" or filing의 period_type값: 위 3경우가 아닐 때

    Raises:
        ValueError:
            - xbrl.period_of_report와 end_date가 일치하는 duration 타입 period가 없는 경우
            - 해당 period에 'days' 필드가 없는 경우
        TypeError:
            - filing이 올바르지 않은 타입인 경우
    """
    xbrl = filing.xbrl()
    doc_end = xbrl.period_of_report

    
    period_at_end = [
        p for p in xbrl.reporting_periods
        if p["type"] == "duration" and p["end_date"] == doc_end
    ]

    if not period_at_end:
        raise ValueError(
            f"[_determine_period_kind] duration 타입의 reporting period를 찾을 수 없습니다. "
            f"filing={filing}, doc_end={doc_end}"
        )

    current = min(period_at_end, key=lambda p: p.get("days", None))

    if current["days"] is None:
        raise ValueError(
            f"[_determine_period_kind] 'days' 필드가 없는 period입니다. "
            f"filing={filing}, doc_end={doc_end}, period={current}"
        )

    if current["days"] <= QUARTER_MAX_DAYS:
        return "QTD"
    elif current["days"] <= YTD_6M_MAX_DAYS:
        return "YTD6"
    elif current["days"] <= YTD_9M_MAX_DAYS:
        return "YTD9"
    else:
        return current.get("period_type","unknown")

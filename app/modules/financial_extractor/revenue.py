
"""
매출(revenue or net income) QTD 계산 모듈
- 매출은 손익계산서의 항목이여서 단순 getter를 해주면 QTD 값을 얻을 수 있다.
- 하지만 QTD를 모든 회사가 보장 해주는 것이 아니기 때문에 QTD인지 xbrl.reporting_periods로 확인이 필요하다.
- xbrl.reporting_periods가 3개월이 아니라면 QTD 값을 계산해주는 함수를 만들어야 한다.

get_revenue는 QTD,YTD를 알려주지 않고 가장 days가 적은 값을 반환한다. => revenue의 QTD만 계산해주려면 get_revenue_qtd 함수를 만들어야 한다.
get_revenue_qtd(filings):
1. xbrl.reporting_periods로 days/fiscal_period를 확인하여 QTD인지 YTD인지 확인한다.
2. days <= 130이면 1개분기(90일)-2개분기(180일)의 사이 이므로 QTD이다.
3. days > 130이면 YTD 값만 있기 때문에 이전 분기의 revenue를 빼서 QTD를 계산해주어야한다.
"""
from edgar import Filing


def _determine_period_kind(filing:Filing) -> str:
    """
    기간의 종류(QTD,YTD)를 결정한다.
    
    Args: Filing(Edgartools Filing 타입)

    Returns: str: QTD or YTD

    Raises: ValueError, TypeError
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

    if current["days"] <= 100:
        return "QTD"
    elif current.get("fiscal_period") in ("YTD6", "YTD9"):
        return "YTD"
    else:
        return current.get("period_type","unknown")

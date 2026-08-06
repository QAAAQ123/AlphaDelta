"""
매출 QTD 계산 모듈
- 매출은 손익계산서의 항목이여서 단순 getter를 해주면 QTD 값을 얻을 수 있다.
- 하지만 QTD를 모든 회사가 보장 해주는 것이 아니기 때문에 QTD인지 xbrl.reporting_periods로 확인이 필요하다.
- xbrl.reporting_periods가 3개월이 아니라면 YTD의 차이를 이용해서 계산해주어야한다.
"""
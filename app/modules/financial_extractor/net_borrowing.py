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
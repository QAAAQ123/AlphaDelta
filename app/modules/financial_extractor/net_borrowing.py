"""
short_term = xbrl.query().by_concept("us-gaap:ShortTermBorrowings").to_dataframe()
long_term = xbrl.query().by_concept("us-gaap:LongTermDebtNoncurrent").to_dataframe()
"""
"""
edgartools 단위 테스트 항목

4. _extract_quarter_from_filing 
    에러
    1. filing.period_of_report가 None/빈 문자열일 때 -> None 리턴
    C
    2. period_str이 YYYY-mm-dd 형식이 아닐 때 -> None 리턴
    정상
    1. 정상 인자가 들어왔을 때 -> period_str에 따라 Enum Quarter
7. _get_cik_and_fiscal_year_end_via_edgartools
    에러
    1. company.get_filings() 결과가 비어있을 때 → None 리턴
    2. 잘못된 ticker -> Value Error -> None 리턴
    3. quarter_enum이 None일 때 -> None 리턴
    정상
    1. ticker가 올바르게 들어왔을 때 -> dict 리턴
"""
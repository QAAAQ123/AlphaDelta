"""
company_sync 단위 테스트 항목
1. _extract_and_clean_df
    1. 잘못된 인자(null)가 들어왔을 때 Exception 후에 []리턴
    2. 아무 내용도 없는 html 데이터가 들어왔을 때 []리턴 
    3. 2개 이상의 html 데이터가 들어왔을 때 2개 이상의 [dict] 리턴
    4. 셀 값이 NaN/None인 경우 'nan' 
2. _extract_quarter_from_filing
    1. 
3. _build_company_create
4. _create_company_entity
5. _persist_company의 예외 처리
"""
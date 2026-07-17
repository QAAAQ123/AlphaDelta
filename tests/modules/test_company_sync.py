"""
company_sync 단위 테스트 항목
1. _extract_and_clean_df
    에러
    1. html_content가 None/잘못된 html -> 예외가 발생했을 때 except Exception이 잡아서 [] 리턴
    2. tables가 빈 테이블 ->  예외가 발생했을 때 exception이 잡아서 [] return
    3. mock col_mapping에 None 포함 -> [] 리턴
    정상
    1. list[dict] 리턴
2. _find_column_mapping
    에러
    1. original_columns가 empty -> None 리턴
    2. 일부 컬럼만 없음 -> 해당 키만 None으로 리턴
    정상
    1. original_columns가 정상 인자일 때 -> dict[str,str] 리턴
    2. 컬럼명 변형('Symbol'이나 'ICB Industry')로 변형 -> fallback 매핑 성공
3. _clean_dataframe
    예외
    1. 컬럼에 NaN이 있을 때 -> ""로 바뀌고 DataFrame 리턴
    정상
    1. 정상 인자가 들어올 때 -> DataFrame 리턴
4. _extract_quarter_from_filing 
    에러
    1. filing.period_of_report가 None/빈 문자열일 때 -> None 리턴
    2. period_str이 YYYY-mm-dd 형식이 아닐 때 -> None 리턴
    정상
    1. 정상 인자가 들어왔을 때 -> period_str에 따라 Enum Quarter
5. _build_company_create   
    정상
    1. 정상 인자가 들어왔을 때 -> Company DTO 리턴
6. _persist_company DB 실제 저장 이외
    에러
    1. IntegrityError 발생 시 → rollback() 호출 + raise
    2. SQLAlchemyError 발생 시 → rollback() 호출 + raise
    정상
    1. 정상 인자가 들어왔을 때 -> company(Company) 리턴
7. _get_cik_and_fiscal_year_end_via_edgartools
    에러
    1. company.get_filings() 결과가 비어있을 때 → None 리턴
    2. 잘못된 ticker -> Value Error -> None 리턴
    3. quarter_enum이 None일 때 -> None 리턴
    정상
    1. ticker가 올바르게 들어왔을 때 -> dict 리턴
"""
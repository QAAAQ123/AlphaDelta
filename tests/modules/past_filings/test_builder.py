"""
단위 테스트 코드
1. _is_amendment_form
    예외1. raw_form이 str 타입이 아닌 인자가 들어올 때 -> AttributeError 발생
    정상1. 10-K,10-Q \A로 끝나지 않는 인자가 들어올 때 -> False return
    정상2. 10-K/A,10-Q/A \A로 끝나는 인자가 들어올 때 -> True return
2. _map_form_type
    예외1. raw_form이 str 타입이 아닌 인자가 들어올 때 -> AttributeError 발생
    정상1. 10-K가 들어올 때 -> FormType.REGULAR_10_K return
    정상2. 10-K/A가 들어올 때 -> FormType.AMENDMENT_10_K_A return
    정상3. 10-Q가 들어올 때 -> FormType.REGULAR_10_Q return
    정상4. 10-Q/A가 들어올 때 -> FormType.AMENDMENT_10_Q_A return
3. _get_parent_form_type
    예외1. child_form_tpye이 FormType이 아닐 때 -> ValueError 발생
    정상1. FormType.AMENDMENT_10_K_A이 들어올 때 -> FormType.REGULAR_10_K return
    정상2. FormType.AMENDMENT_10_Q_A이 들어올 때 -> FormType.REGULAR_10_Q return
    정상3. FormType.REGULAR_10_Q or REGULAR_10_K가 들어올 때 -> 인자를 그대로 return
4. _parse_year_and_quarter
    예외1. period_of_report이 YYYY-mm-dd 형식이 아닐 때 -> ValueError 발생
    예외2. period_of_report이 str type이 아닐 때 -> AttributeError 발생
    예외3. period_of_report이 존재할 수 없는 날짜일 때 -> ValueError 발생
    정상 상황: period_of_report의 mm이 1-12 중 하나이고 존재하는 연도와 일일 때 -> (report_date.year, Quarter) tuple return
5. classify_and_build_original_filings
    filing_data가 None인 경우는 service에서 거르기 때문에 검사 불필요
    예외1. filing_data가 None인 경우 -> TypeError 발생 (NoneType은 반복 가능한 객체가 아님)
    예외2. company_id가 None이거나 int가 아닌 경우 -> pydantic.ValidationError 발생 (`FilingCreate` 생성 시 타입 검증 실패)
    정상1. filing_data:정상 공시20개/existing_accessions:None -> len(original_filings): 20개, amendment_filings: 0개
    정상2. filing_data:정상 공시20개,수정공시 2개/existing_accessions:None -> len(original_filings): 20개, amendment_filings: 2개
    정상3. filing_data:정상 공시 10개/existing_accessions:10개(모두 겹침) -> len(original_filings): 0개, amendment_filings: 0개
    정상4. filing_data:정상 공시 10개/existing_accessions:10개(모두 안겹침) -> len(original_filings): 10개, amendment_filings: 0개
6. build_amendment_filings
    예외1. company_id만 None | int아님 -> pydantic.ValidationError 발생 (`FilingCreate` 생성 시 company_id 타입 검증 실패)
    예외2. parent_map이 None -> AttributeError 발생 (NoneType에 대해 `.get` 호출 시)
    정상1. amendment_filings이 None -> 빈 list return
    정상2. amendment_filings이 3개 -> 길이 3의 amendment_schemas return
7. build_parent_map
    예외1. flings이 None -> TypeError 발생 (NoneType은 반복 가능한 객체가 아님)
    정상1. filing이 정상 -> (form_tye,year,quarter): id 튜플의 dict
"""
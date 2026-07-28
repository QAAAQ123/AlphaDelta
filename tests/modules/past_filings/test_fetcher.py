"""
단위 테스트 코드
1. fetch_past_20_quarters_filings_info
    정상1. get_filings에서 정상 데이터가 반환될 때 -> not_amended_filings 20개 + amended_filings 필터 후 합산 반환
    정상2. amended_filings에 period_of_report가 not_amended_filings 대상 기간과 일치하지 않는 경우 -> 최종 리스트에 포함되지 않음
    예외1. edgartools 호출 중 예외가 발생할 때 -> 빈 리스트 반환

2. _extract_periods
    정상1. filings 목록에 period_of_report가 모두 있을 때 -> 중복 제거된 set 반환

3. _filter_amendments_by_period
    정상1. amended_filings가 target_periods에 일치하는 항목만 반환
    정상2. amended_filings가 target_periods에 하나도 일치하지 않을 때 -> 빈 리스트 반환
"""
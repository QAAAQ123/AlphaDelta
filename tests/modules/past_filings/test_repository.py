"""
단위 테스트 코드
1. get_existing_filings
    정상1. 회사 ID에 해당하는 Filing이 있을 때 -> 해당 Filing 리스트 반환
    정상2. 해당 회사 ID에 Filing이 없을 때 -> 빈 리스트 반환

2. bulk_save_original_filings
    정상1. original_filings 리스트가 정상일 때 -> filing_crud.bulk_create_filings가 호출되어 생성된 리스트 반환
    예외1. original_filings가 None일 때 -> filing_crud.bulk_create_filings 호출 시 TypeError 또는 pydantic.ValidationError 발생 가능

3. bulk_save_amendment_filings
    정상1. amendment_filings이 비어 있을 때 -> 아무 작업도 하지 않음
    정상2. amendment_filings에 항목이 있을 때 -> filing_crud.bulk_create_filings가 호출되어 저장

4. commit_filings
    정상1. db.commit 호출

5. rollback_filings
    정상1. db.rollback 호출
"""
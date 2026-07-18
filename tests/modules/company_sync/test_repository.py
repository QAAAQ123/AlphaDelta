"""
repository 단위 테스트 항목
5. _build_company_create   
    정상
    1. 정상 인자가 들어왔을 때 -> Company DTO 리턴
6. _persist_company DB 실제 저장 이외
    에러
    1. IntegrityError 발생 시 → rollback() 호출 + raise
    2. SQLAlchemyError 발생 시 → rollback() 호출 + raise
    정상
    1. 정상 인자가 들어왔을 때 -> company(Company) 리턴
"""
import gc
import time
from app.core.database import SessionLocal
from app.core import logger
from app.crud import company as company_crud
from app.modules.past_filings import fetcher, builder, repository


def initialize_past_filings(ticker: str):
    """
    과거 20분기(5년) 공시 데이터를 조회하여 DB에 저장합니다.

    각 기업별로:
    1. DB에서 기존 공시를 먼저 조회합니다 — 최근 원본 공시가 충분(>=20)하면 외부 조회를 건너뜁니다.
    2. 필요 시 edgartools를 통해 공시 정보 조회
    3. 원본/수정공시 분류 및 스키마 생성(기존 accession은 건너뜀)
    4. 원본 공시 먼저 저장하고 생성된 ID로 부모 맵핑 생성
    5. 수정공시를 부모 ID와 함께 저장
    6. 트랜잭션 커밋
    """

    logger.info("기업별 과거 5개년(20분기) 데이터 수집 시작")

    with SessionLocal() as init_db:
        existing_companies = company_crud.get_all_from_company(init_db)
        existing_companies_dict = {
            company.ticker: {"cik": str(company.cik), "id": company.id}
            for company in existing_companies
        }

    for ticker, info in existing_companies_dict.items():
        cik = info["cik"]
        company_id = info["id"]

        with logger.contextualize(domain="Filing", ticker=ticker):
            with SessionLocal() as db:
                # [1단계] 기존 공시 조회 (먼저) — DB에 충분히 있으면 외부 API 호출을 건너뜀
                existing_db_filings = repository.get_existing_filings(db, company_id)
                existing_accessions = {f.accession_number for f in existing_db_filings}
                parent_map = {
                    (f.form_type, f.year, f.quarter): f.id
                    for f in existing_db_filings if f.amends_filing_id is None
                }

                # 원본(수정이 없는) 공시 개수로 외부 호출 필요 여부 판단
                original_count = len([f for f in existing_db_filings if f.amends_filing_id is None])
                if original_count >= 20:
                    logger.info("DB에 최근 20개 원본 공시가 이미 존재하여 외부 조회를 건너뜁니다")
                    continue

                # [2단계] 공시 정보 조회 (필요 시)
                filing_data = fetcher.fetch_past_20_quarters_filings_info(cik, ticker)

                if not filing_data:
                    continue

                try:

                    # [3단계] 원본/수정공시 분류 및 스키마 생성
                    original_filings, amendment_filings = builder.classify_and_build_original_filings(
                        filing_data, company_id, existing_accessions
                    )

                    # [4단계] 원본 공시 저장 및 ID 매핑
                    db_originals = repository.bulk_save_original_filings(db, original_filings)
                    db.flush()  # DB에 임시 반영하여 생성된 ID 로드

                    # [5단계] 부모 ID 맵핑 업데이트
                    if db_originals:
                        new_parent_map = builder.build_parent_map(db_originals)
                        parent_map.update(new_parent_map)

                    # [6단계] 수정공시 저장
                    amendment_schemas = builder.build_amendment_filings(
                        amendment_filings, company_id, parent_map
                    )
                    repository.bulk_save_amendment_filings(db, amendment_schemas)

                    # [7단계] 최종 커밋
                    repository.commit_filings(db)
                    total_count = len(original_filings) + len(amendment_schemas)
                    logger.bind(total_count=total_count).success("자기참조 매핑 및 일괄 적재 완료")

                except Exception:
                    repository.rollback_filings(db)
                    logger.exception("DB 적재 실패로 전체 롤백")

                del filing_data
                gc.collect()

                logger.debug("시스템 안정화를 위해 2초간 대기")
                time.sleep(2.0)

        logger.success("초기 Filing 데이터 적재 완료")
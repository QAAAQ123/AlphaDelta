from datetime import datetime
import sys
import os
from loguru import logger
from edgar import Company
from app.models.base import AnalysisStatus, Filing, Quarter, FormType
from app.schemas import FilingCreate
import uuid
import gc
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings, setup_global_mdc_logging, _request_id
from app.core.database import SessionLocal
from app.crud import company as company_crud
from app.crud import filing as filing_crud


# 과거 20분기 Filing과 Finace 테이블 저장
def fetch_past_20_quarters_filings():

    token = _request_id.set(str(uuid.uuid4())[:8])

    with logger.contextualize(domain="Filing"):
        logger.info("과거 5개년(20분기) 전체 기업 데이터 수집 시작")

        with SessionLocal() as init_db:
            existing_companies = company_crud.get_all_from_company(init_db)
            existing_companies_dict = {
                company.ticker: {"cik": str(company.cik), "id": company.id}
                for company in existing_companies
            }

        for ticker, info in existing_companies_dict.items():
            cik = info["cik"]
            company_id = info["id"]

            with SessionLocal() as db:
                filing_data = get_past_20_quarters_filings_info(cik, ticker)

                if not filing_data:
                    continue

                original_filings = []
                amendment_filings = []

                try:
                    # [1단계] 원본과 수정 공시 분류 및 원본 스키마 생성
                    for filing in filing_data:
                        report_date = datetime.strptime(
                            filing.period_of_report, "%Y-%m-%d"
                        )
                        calc_year = report_date.year
                        q_num = (report_date.month - 1) // 3 + 1
                        mapped_quarter = Quarter[f"Q{q_num}"]

                        # FormType 매핑
                        raw_form = filing.form
                        is_amend = raw_form.endswith("/A")
                        if raw_form in ["10-K", "10-K/A"]:
                            mapped_form = (
                                FormType.AMENDMENT_10_K_A
                                if is_amend
                                else FormType.REGULAR_10_K
                            )
                        else:
                            mapped_form = (
                                FormType.AMENDMENT_10_Q_A
                                if is_amend
                                else FormType.REGULAR_10_Q
                            )

                        if not is_amend:
                            # 1-1. 원본 공시는 바로 스키마 생성
                            new_filing = FilingCreate(
                                accession_number=filing.accession_number,
                                form_type=mapped_form,
                                primary_document=filing.document.document_type,
                                year=calc_year,
                                quarter=mapped_quarter,
                                filing_date=filing.filing_date,
                                analysis_status=AnalysisStatus.NOT_ANALYZED,
                                parent_id=None,
                                company_id=company_id,
                            )
                            original_filings.append(new_filing)
                        else:
                            # 1-2. 수정 공시는 잠시 보관
                            amendment_filings.append(filing)

                    # [2단계] 원본 공시 먼저 Bulk Insert 진행
                    # 💡 주의: crud 내부에서 db.add_all()을 쓰고 commit은 하지 않은 상태여야 합니다.
                    db_originals = filing_crud.bulk_create_filings(db, original_filings)

                    # 💡 핵심: db.flush()를 호출하면 DB에 데이터가 임시 반영되면서 생성된 ID(PK)들이 메모리에 로드됩니다.
                    db.flush()

                    # [3단계] 생성된 부모 ID들을 딕셔너리에 맵핑 고속화 기법
                    # Key 기준: (공시종류_연도_분기) -> 예: (FormType.REGULAR_10_Q, 2025, Quarter.Q1): DB_ID
                    parent_map = {
                        (obj.form_type, obj.year, obj.quarter): obj.id
                        for obj in db_originals
                    }

                    # [4단계] 수정 공시들의 parent_id를 매핑하여 Bulk Insert 진행
                    amendment_schemas = []
                    for filing in amendment_filings:
                        report_date = datetime.strptime(
                            filing.period_of_report, "%Y-%m-%d"
                        )
                        calc_year = report_date.year
                        q_num = (report_date.month - 1) // 3 + 1
                        mapped_quarter = Quarter[f"Q{q_num}"]

                        # 이 수정공시가 바라봐야 할 부모(원본)의 FormType 유추
                        parent_form_type = (
                            FormType.REGULAR_10_K
                            if filing.form in ["10-K", "10-K/A"]
                            else FormType.REGULAR_10_Q
                        )

                        # 맵핑 딕셔너리에서 부모 ID 추출
                        parent_id = parent_map.get(
                            (parent_form_type, calc_year, mapped_quarter)
                        )

                        # 수정공시 전용 FormType 결정
                        mapped_form = (
                            FormType.AMENDMENT_10_K_A
                            if filing.form in ["10-K", "10-K/A"]
                            else FormType.AMENDMENT_10_Q_A
                        )

                        amend_schema = FilingCreate(
                            accession_number=filing.accession_number,
                            form_type=mapped_form,
                            primary_document=filing.document.document_type,
                            year=calc_year,
                            quarter=mapped_quarter,
                            filing_date=filing.filing_date,
                            analysis_status=AnalysisStatus.NOT_ANALYZED,
                            parent_id=parent_id,  # 💡 발급받은 부모 ID 대입!
                            company_id=company_id,
                        )
                        amendment_schemas.append(amend_schema)

                    # 수정 공시가 존재한다면 최종 Bulk 저장
                    if amendment_schemas:
                        filing_crud.bulk_create_filings(db, amendment_schemas)

                    # [5단계] 한 회사의 원본+수정 공사가 모두 완벽할 때 한 방에 최종 커밋!
                    db.commit()
                    total_count = len(original_filings) + len(amendment_schemas)
                    logger.success(
                        f"[{ticker}] 자기참조 매핑 및 일괄 적재 완료: 총 {total_count}개"
                    )
                except Exception as e:
                    db.rollback()
                    logger.exception(f"DB 적재 실패로 전체 롤백")

                del filing_data
                gc.collect()

                logger.info("시스템 안정화를 위해 2초간 대기")
                time.sleep(2.0)

        logger.success("초기 Filing 데이터 적재 완료")


def get_past_20_quarters_filings_info(cik: str, ticker: str):
    with logger.contextualize(domain="Filing", ticker=ticker):
        try:
            company = Company(cik)

            all_filings = company.get_filings(form=["10-K", "10-Q"], amendments=True)
            target_filings = all_filings.filter(date=":2026-05-31")
            processed_data = []
            pure_quter_count = 0

            for filing in target_filings.head(40):

                if pure_quter_count >= 20:
                    break

                is_amendment = filing.form.endswith("/A")

                if not is_amendment:
                    pure_quter_count += 1
                    logger.info(f" 원본 공시({pure_quter_count/20}): {filing.form}")
                else:
                    logger.info(f" 수정 공시 감지-수집 한도 확장")
                processed_data.append(filing)

            logger.success(
                f"최종 수집 완료: 총 {len(processed_data)}개 (원본 {len(processed_data)}개 + 수정공시 {len(processed_data) - 20}개)"
            )
            return processed_data
        except Exception as e:
            logger.warning(f"Filing 수집 중 치명적 오류 발생: {e}")
        return []


if __name__ == "__main__":
    setup_global_mdc_logging()
    settings
    fetch_past_20_quarters_filings()

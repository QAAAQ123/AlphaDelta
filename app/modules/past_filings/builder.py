from datetime import datetime
from loguru import logger
from app.models.base import AnalysisStatus, Filing, Quarter, FormType
from app.schemas import FilingCreate
from sqlalchemy.orm import Session


def classify_and_build_original_filings(
    filing_data: list,
    company_id: int,
    existing_accessions: set[str]
) -> tuple[list[FilingCreate], list]:
    """
    공시 데이터를 원본과 수정공시로 분류하고 원본 FilingCreate 스키마를 생성합니다.
    
    Args:
        filing_data: edgartools에서 조회한 공시 객체 리스트
        company_id: 기업의 DB ID
        existing_accessions: 기존 DB에 있는 accession_number 세트
        
    Returns:
        (원본 FilingCreate 리스트, 수정공시 객체 리스트) 튜플
    """
    original_filings = []
    amendment_filings = []

    for filing in filing_data:
        # 이미 DB에 있는 공시는 건너뛰기
        if filing.accession_number in existing_accessions:
            continue

        report_date = datetime.strptime(filing.period_of_report, "%Y-%m-%d")
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
            # 원본 공시 스키마 생성
            new_filing = FilingCreate(
                accession_number=filing.accession_number,
                form_type=mapped_form,
                primary_document=filing.document.document_type,
                year=calc_year,
                quarter=mapped_quarter,
                filing_date=filing.filing_date,
                analysis_status=AnalysisStatus.NOT_ANALYZED,
                amends_filing_id=None,
                company_id=company_id,
            )
            original_filings.append(new_filing)
        else:
            # 수정 공시는 임시 보관 (부모 ID 매핑 필요)
            amendment_filings.append(filing)

    return original_filings, amendment_filings


def build_amendment_filings(
    amendment_filings: list,
    company_id: int,
    parent_map: dict
) -> list[FilingCreate]:
    """
    수정공시 데이터를 부모 ID와 함께 FilingCreate 스키마로 변환합니다.
    
    Args:
        amendment_filings: 수정공시 객체 리스트
        company_id: 기업의 DB ID
        parent_map: (FormType, year, quarter) -> parent_id 매핑 딕셔너리
        
    Returns:
        수정공시 FilingCreate 리스트
    """
    amendment_schemas = []

    for filing in amendment_filings:
        report_date = datetime.strptime(filing.period_of_report, "%Y-%m-%d")
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
            amends_filing_id=parent_id,  # 부모 ID 대입
            company_id=company_id,
        )
        amendment_schemas.append(amend_schema)

    return amendment_schemas


def build_parent_map(db_originals: list[Filing]) -> dict:
    """
    생성된 원본 공시들을 기반으로 부모 ID 매핑을 생성합니다.
    
    Args:
        db_originals: DB에 저장된 원본 Filing 객체 리스트
        
    Returns:
        (FormType, year, quarter) -> id 매핑 딕셔너리
    """
    parent_map = {}
    if db_originals:
        for obj in db_originals:
            parent_map[(obj.form_type, obj.year, obj.quarter)] = obj.id
    return parent_map

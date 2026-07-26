from datetime import datetime
from app.models.base import AnalysisStatus, Filing, Quarter, FormType
from app.schemas import FilingCreate


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

        calc_year, mapped_quarter = _parse_year_and_quarter(filing.period_of_report)
        mapped_form = _map_form_type(filing.form)
       
        if not _is_amendment_form(filing.form):
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
        calc_year, mapped_quarter = _parse_year_and_quarter(filing.period_of_report)
        mapped_form = _map_form_type(filing.form)

        # 이 수정공시가 바라봐야 할 부모(원본)의 FormType 유추
        parent_form_type = _get_parent_form_type(mapped_form)

        # 맵핑 딕셔너리에서 부모 ID 추출
        parent_id = parent_map.get(
            (parent_form_type, calc_year, mapped_quarter)
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


def build_parent_map(filings: list[Filing]) -> dict:
    """
    생성된 원본 공시들을 기반으로 부모 ID 매핑을 생성합니다.
    
    Args:
        filings: DB에 저장된 원본 Filing 객체 리스트
        
    Returns:
        (FormType, year, quarter) -> id 매핑 딕셔너리
    """
    return{
        (f.form_type, f.year, f.quarter): f.id
        for f in filings 
    }


def _is_amendment_form(raw_form: str) -> bool:
    """공시 서식이 수정 공시(/A)인지 여부를 판단합니다."""
    return raw_form.endswith("/A")

def _map_form_type(raw_form: str) -> FormType:
    """Raw 서식 문자열을 시스템 내부 FormType Enum으로 매핑합니다."""
    # FormType 매핑
    is_amend = _is_amendment_form(raw_form)
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
    return mapped_form

def _get_parent_form_type(child_form_type: FormType) -> FormType:
    """수정 공시(Child)의 FormType을 바탕으로 부모(Parent) 원본 공시의 FormType을 추론합니다."""
    if child_form_type == FormType.AMENDMENT_10_K_A:
        return FormType.REGULAR_10_K
    elif child_form_type == FormType.AMENDMENT_10_Q_A:
        return FormType.REGULAR_10_Q
    return child_form_type  # 이미 원본인 경우 그대로 반환


def _parse_year_and_quarter(period_of_report: str) -> tuple[int, Quarter]:
    """보고 기간(YYYY-MM-DD)을 파싱하여 연도와 Quarter Enum을 반환합니다."""
    report_date = datetime.strptime(period_of_report, "%Y-%m-%d")
    q_num = (report_date.month - 1) // 3 + 1

    return report_date.year, Quarter[f"Q{q_num}"]


from edgar import get_by_accession_number
from edgar.xbrl import StandardConcept
from loguru import logger
import pandas as pd
import re
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.models.base import Filing,Quarter,FormType,Finance

@dataclass
#여러 재무 지표 추출 함수에서 공통으로 쓰는 결과 타입
class FinanceResult:
    value: int
    date: str
    cross_validated: bool


class FinancialDataExtractor:
    """
    edgartools를 활용하여 SEC 공시에서 
    finaces 테이블에 필요한 핵심 재무 지표를 추출하는 서비스 모듈
    """

    def __init__(self):
        pass

    _QUARTERLY_FORM_TYPES = (FormType.REGULAR_10_Q, FormType.AMENDMENT_10_Q_A)

    _QUARTER_ORDER = [Quarter.Q1, Quarter.Q2, Quarter.Q3, Quarter.Q4]

    # 우선순위 2: US-GAAP 표준 태그 유사 패턴
    _CONCEPT_REGEX: re.Pattern[str] = re.compile(
        r"NetCashProvidedByUsedInOperatingActivities.*", 
        re.IGNORECASE
    )
    
    # 우선순위 3: 사람이 읽는 Label 텍스트용 패턴
    # (Net Cash/Cash Provided/Used + Operating Activities 조합 대응)
    _LABEL_REGEX: re.Pattern[str] = re.compile(
        r"(?=.*(net\s+cash|cash\s+(provided|used)))?=.*operating\s+activities", 
        re.IGNORECASE
    )

    @staticmethod
    def _refine_operating_cash_flow_data(cashflow_statement, sorted_date_header_list) -> list[list]:
        """
        standard_concept -> concept -> label 순으로 operating cash flow 찾아
        날짜를 기준으로 [[date, number]] 배열을 만드는 함수
        """
        # 1. 내부에서 필요한 칼럼만 명시적으로 슬라이싱
        metadata_cols = ["concept", "label", "standard_concept"]
        available_meta = [col for col in metadata_cols if col in cashflow_statement.columns]
        target_columns = available_meta + sorted_date_header_list
        df = cashflow_statement[target_columns].copy()

        # 2. Operating Cash Flow 행 찾기 (우선순위 기반 필터링)
        target_row = pd.DataFrame()

        # 우선순위 1: standard_concept가 CASH_FROM_OPERATIONS인 행
        logger.debug("우선순위 1(standard concept)로 ocf 찾기 시작")
        if "standard_concept" in df.columns:
            ocf_name = StandardConcept.CASH_FROM_OPERATIONS.name
            target_row = df[
                (df["standard_concept"] == StandardConcept.CASH_FROM_OPERATIONS)
                | (df["standard_concept"] == ocf_name)
            ]

        # 우선순위 2: 정규식 기반 xbrl concept 이름 추적 (NetCashProvidedByUsedInOperatingActivities 등)
        if target_row.empty and "concept" in df.columns:
            logger.debug("우선순위1 실패 - 우선순위 2(concept)로 ocf 찾기 시작")
            concept_regex = r"NetCashProvidedByUsedInOperatingActivities.*"
            target_row = df[df["concept"].str.contains(concept_regex, case=False, na=False, regex=True)]

        # 우선순위 3: 정규식 기반 human label 텍스트 추적 (Net Cash / Provided / Used + Operating 조합)
        if target_row.empty and "label" in df.columns:
            logger.debug("우선순위2 실패 - 우선순위 3(label))로 ocf 찾기 시작")
            label_regex = r"(?=.*(net\s+cash|cash\s+(provided|used)))?=.*operating\s+activities"
            target_row = df[df["label"].str.contains(label_regex, case=False, na=False, regex=True)]

        # 행을 찾지 못한 경우 빈 배열 리턴
        if target_row.empty:
            logger.warning("현금흐름표에서 Operating Cash Flow 항목을 찾을 수 없습니다.")
            return []

        # 3. 최적의 행이 여러 개 잡혔을 경우 첫 번째 행을 기준으로 채택
        selected_row = target_row.iloc[0]
        logger.debug(
            f"[matched] concept={selected_row.get('concept')}, "
            f"label={selected_row.get('label')}, "
            f"standard_concept={selected_row.get('standard_concept')}"
        )
        # 4. sorted_date_header_list를 순회하며 [[date, value]] 구조 생성
        result = []
        for date_col in sorted_date_header_list:
            value = selected_row.get(date_col)

            if pd.isna(value):
                processed_value = 0
            else:
                try:
                    processed_value = int(float(value))
                except (ValueError, TypeError):
                    processed_value = value

            result.append([date_col, processed_value])

        return result

    @staticmethod
    def _sort_date_header_list(original_header_list: list[str]) -> list[str]:
        def date_sort_key(item: str):
            """
            날짜는 그대로 사전순 정렬하고, 
            접미사는 Q1(1등) -> YTD(2등) -> 없음(3등) 순으로 정렬하기 위한 키 함수
            """
            # 1. 날짜 부분 추출 (앞의 10자리: YYYY-MM-DD)
            date_part = item[:10]
            
            # 2. 접미사에 따른 우선순위 부여 (숫자가 낮을수록 앞에 정렬됨)
            if any(q in item for q in ["(Q1)", "(Q2)", "(Q3)", "(Q4)"]):
                suffix_priority = 1  # 분기가 최우선 (1등)
            elif "(YTD)" in item:
                suffix_priority = 2  # 누적이 그다음 (2등)
            else:
                suffix_priority = 3  # 없음이 마지막 (3등)
                
            # (날짜, 접미사 우선순위) 튜플을 반환
            return (date_part, suffix_priority)   

        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}")
        date_list = []

        for value in original_header_list:
            if date_pattern.match(value):
                date_list.append(value)
        date_list.sort(key=date_sort_key)
        return date_list
     

    @classmethod
    def _get_target_quarters(cls, filing_year: int, filing_quarter: Quarter) -> list[tuple[int, "Quarter"]]:
        """
        10-K의 (year, quarter)를 기준으로 직전 3개 분기의 (year, quarter)를 
        시간 역순(최근 -> 과거)으로 반환.
        예: (2025, Q2) -> [(2025, Q1), (2024, Q4), (2024, Q3)]
        """
        cur_idx = cls._QUARTER_ORDER.index(filing_quarter)
        cur_year = filing_year
        targets = []
        for _ in range(3):
            cur_idx -= 1
            if cur_idx < 0:
                cur_idx = 3
                cur_year -= 1
            targets.append((cur_year, cls._QUARTER_ORDER[cur_idx]))
        return targets


    def _get_prior_quarters_ocf_sum(self, db: Session, accession_number: str) -> int:
        current_filing = (
            db.query(Filing).filter(Filing.accession_number == accession_number).first()
        )
        if current_filing is None:
            raise ValueError(f"[{accession_number}] DB에서 현재 filing 레코드를 찾을 수 없습니다.")

        targets = self._get_target_quarters(current_filing.year, current_filing.quarter)

        total = 0
        for target_year, target_quarter in targets:
            effective_filing = self._find_effective_quarterly_filing(
                db, current_filing.company_id, target_year, target_quarter
            )
            if effective_filing is not None and effective_filing.finance is not None:
                ocf_value = effective_filing.finance.ocf
                logger.debug(
                    f"[{accession_number}] {target_year} {target_quarter.value} OCF={ocf_value} "
                    f"(source={effective_filing.accession_number})"
                )
            else:
                logger.warning(
                    f"[{accession_number}] {target_year} {target_quarter.value} OCF 데이터가 DB에 없음 - 수동 입력 요청"
                )
                ocf_value = self._prompt_manual_ocf_input(target_year, target_quarter)

            total += ocf_value

        return total
    
    def _find_effective_quarterly_filing(
        self, db: Session, company_id: int, year: int, quarter: "Quarter"
    ) -> Filing | None:
        candidates = (
            db.query(Filing)
            .filter(
                Filing.company_id == company_id,
                Filing.year == year,
                Filing.quarter == quarter,
                Filing.form_type.in_(self._QUARTERLY_FORM_TYPES),
            )
            .all()
        )
        if not candidates:
            return None

        # 다른 필링에게 정정당한(=amends_filing_id로 지목된) 필링은 제외
        amended_ids = {f.amends_filing_id for f in candidates if f.amends_filing_id is not None}
        effective = [f for f in candidates if f.id not in amended_ids]

        if len(effective) > 1:
            logger.warning(
                f"{year} {quarter.value} 분기에 유효 필링이 여러 개 발견됨: "
                f"{[f.accession_number for f in effective]} - filing_date 최신순 채택"
            )
            effective.sort(key=lambda f: f.filing_date, reverse=True)

        return effective[0] if effective else None

    def extract_operating_cash_flow(self, accession_number: str, is_10_k: bool, db: Session) -> FinanceResult:
        """
        - OCF를 추출하는 함수
        - edgartools에서 get_operating_cash_flow()와 statements.to_dataframe()을 사용하여 
        교차 검증을 한 ocf를 추출하는 함수
        """
        """
        1. get_operating_cash_flow()로 값 가져옴
        2. statements.to_dataframe()에서 
        3. df Series에서 날짜를 sort([-1]이 최신 날짜 인덱스)
        4. standard_concept -> concept -> label 순으로 operating cash flow 찾아 
        날짜를 기준으로 [[date,number]]배열을 만듦
        6. 1에서 가져온 값과 4의 [0]을 비교
            1. 두 값이 일치하면: 신뢰성이 검증되었으므로 그 값 그대로 return
            2. 두 값이 다르면: 라이브러리 내장 수치에 정합성 오류(과거 데이터 오인 등)가 발생한 것이므로, 
                오류 로그를 출력하고 4에서 나온 가장 최신 값을 return

        만약 10-K이면 과거 재무 데이터 불러와서 계산해야함
        과거 3개분기 재무 데이터가 없다면 초기 데이터이므로 수동 입력
        """
        filing = get_by_accession_number(accession_number)

        #1. Cash flow statement를 Dataframe(summary)로 가져옴
        try:
            cashflow_statement = pd.DataFrame(filing.xbrl().statements.cashflow_statement().to_dataframe(view="summary"))
        except Exception as e:
            logger.exception(f"[{accession_number}] Cashflow Statement 요청 및 데이터프레임 변환 중 예외 발생: {e}")
            raise
        #2. df Series에서 날짜를 sort
        original_header_list = cashflow_statement.columns.astype(str).tolist()
        sorted_date_header_list = self._sort_date_header_list(original_header_list)
    
        if not sorted_date_header_list:
            logger.error(f"[{accession_number}] 날짜 형식 컬럼을 찾지 못함: {original_header_list}")
            raise ValueError(f"[{accession_number}] Cashflow statement에서 날짜 컬럼을 찾을 수 없습니다.")
        #3. [[date,number_data]]로 ocf를 찾음
        refined_data = self._refine_operating_cash_flow_data(cashflow_statement,sorted_date_header_list)
        if not refined_data:
            logger.error(f"[{accession_number}] ocf 데이터를 정제하지 못함 (검색 대상 컬럼: {sorted_date_header_list})")
            raise ValueError(f"[{accession_number}] Operating Cash Flow 데이터를 찾을 수 없습니다.")
        
        logger.debug(f"[{accession_number}] 최신 날짜순으로 정렬된 ocf 데이터 정제 완료: {refined_data}")
        #4. get_operating_cash_flow()로 값 가져온 값과 refined_data의 가장 최신 값 비교
        try:
            operating_cash_flow_by_getter = filing.financials.get_operating_cash_flow()
        except Exception as e:
            logger.exception(f"[{accession_number}] Edgartools get_operating_cash_flow 요청 중 에러 발생: {e}")
            raise
        latest_value = refined_data[-1][1]
        latest_date = refined_data[-1][0]

        if is_10_k == False: #10-Q일 때
            if operating_cash_flow_by_getter is None:
                logger.info(f"[{accession_number}] getter가 OCF를 반환하지 않음 - dataframe 값으로 대체")
            elif latest_value == operating_cash_flow_by_getter:
                logger.info(f"[{accession_number}] Edgartools와 Dataframe으로 가져온 최신 ocf가 같음")
                return FinanceResult(latest_value,latest_date,True)
            else:
                logger.info(
                    f"[{accession_number}] OCF 불일치 - getter={operating_cash_flow_by_getter}, "
                    f"dataframe(latest)={latest_value} (date={latest_date}). "
                    f"Dataframe 값으로 fallback.")
                return FinanceResult(latest_value,latest_date,False)
        else:  # 10-K일 때
            annual_ocf = latest_value
            prior_quarters_sum = self._get_prior_quarters_ocf_sum(db, accession_number)
            last_quarter_ocf = annual_ocf - prior_quarters_sum

            logger.info(
                f"[{accession_number}] 10-K 연간 OCF={annual_ocf}, "
                f"직전 3분기 합={prior_quarters_sum} -> 마지막 분기 OCF={last_quarter_ocf}"
            )
            # getter(연간 누적값)와 dataframe(연간 누적값)은 이미 latest_value로 일원화되어 있으므로
            # cross_validated는 "분기 역산값"에 대한 검증이 아니라 False로 표기
            return FinanceResult(last_quarter_ocf, latest_date, False)

            


        
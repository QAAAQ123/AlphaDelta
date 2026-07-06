from edgar import *
from loguru import logger
import pandas as pd
import re

class FinancialDataExtractor:
    """
    edgartools를 활용하여 SEC 공시에서 
    finaces 테이블에 필요한 핵심 재무 지표를 추출하는 서비스 모듈
    """

    def __init__(self):
        pass
   
    @staticmethod
    def _refine_operating_cash_flow_data(original_header_list: list[str], sorted_date_header_list: list[str], cashflow_statement: pd.DataFrame) -> list[list[str,str]]
        """standard_concept -> concept -> label 순으로 operating cash flow 찾아 날짜를 기준으로 [[date,number]]배열을 만드는 함수"""
        pass
     

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
     

    def extract_operating_cash_flow(self, accession_number: str, is_10_k: bool):
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
        6. 1에서 가져온 값과 4의 [-1]을 비교
            1. 두 값이 일치하면: 신뢰성이 검증되었으므로 그 값 그대로 return
            2. 두 값이 다르면: 라이브러리 내장 수치에 정합성 오류(과거 데이터 오인 등)가 발생한 것이므로, 
                오류 로그를 출력하고 즉시 파싱실패 예외 처리(Circuit Breaker 작동)

        만약 10-K이면 과거 재무 데이터 불러와서 계산해야함
        과거 3개분기 재무 데이터가 없다면 초기 데이터이므로 수동 입력
        """
        filing = get_by_accession_number(accession_number)

        #1. get_operating_cash_flow()로 값 가져옴
        operating_cash_flow_by_getter = filing.financials.get_operating_cash_flow()
        #2. Cash flow statement를 Dataframe(summary)로 가져옴
        try:
            cashflow_statement = pd.DataFrame(filing.xbrl().statements.cashflow_statement().to_dataframe(view="summary"))
        except Exception as e:
            logger.warning(f"Cashflow Statement 요청 및 데이터프레임 변환 중 예외 발생")
            raise
        #3. df Series에서 날짜를 sort([-1]이 최신 날짜 인덱스)
        original_header_list = cashflow_statement.columns.astype(str).toList()
        sorted_date_header_list = self._sort_date_header_list(original_header_list)
        refined_data = self._refine_operating_cash_flow_data(original_header_list,sorted_date_header_list,cashflow_statement)

        
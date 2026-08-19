import pytest
from app.modules.financial_extractor.cash_flow_statement import (
    _convert_to_qtd,
    _determine_quarter,
    _determine_quarter_from_months,
    _extract_month,
    _select_most_recent_filing,
    _filter_candidate_filings_by_quarter_offset,
    _find_prior_period_filing,
    _find_prior_filing_candidates,
    _get_financials,
    get_items_qtd_cash_flow_statement
)
from app.models.enum import *
from edgar import Filing,Company,Financials

MODULE_PATH = "app.modules.financial_extractor.cash_flow_statement"



@pytest.fixture
def create_filing(mocker):
    def _filing_factory(
            form: str = None, 
            fiscal_year_end: str = None, 
            period_of_report: str = None, 
            filing_date: str = None
        ):
        filing = mocker.MagicMock(spec=Filing)
        company = mocker.MagicMock(spec=Company)

        filing.company = company        
        company.fiscal_year_end = fiscal_year_end

        filing.form = form
        filing.period_of_report = period_of_report
        filing.filing_date = filing_date

        return filing
    return _filing_factory

"""
def _convert_to_qtd(
        current_financials: Financials, 
        prior_financials: Financials | None, 
        current_quarter: Quarter, 
        getter: Callable[[Financials], int | float | None]
    ) -> int | float | None:
1. edgartools에서 Exception 발생 -> raise RuntimeError
2. Q1일 때 -> current_ytd 그대로 return
3. Q2-Q4일 때 -> curr - prior QTD 계산 정확도
4. prior_ytd가 None이면 -> None 반환
5. current_ytd가 None이면 -> None 반환

차순위
1. prior_ytd, current_ytd가 복잡한 숫자일 때 예상한대로 계산
"""
class TestConvertToQtd():
    def test_raise_exception_when_unexpected_edgartools_error(self,mocker):
        #1. edgartools에서 Exception 발생 -> raise exception
        mock_getter = mocker.MagicMock(side_effect=Exception("unexpected exception occured "))

        with pytest.raises(RuntimeError, match="Edgartools 요청 중 예상하지 못한 문제 발생"):
            _convert_to_qtd("curr_stub",  "prior_stub", Quarter.Q2, mock_getter)

    def test_return_current_ytd_when_quarter_is_q1(self,mocker):
        #Q1일 때 -> current_ytd 그대로 return
        mock_getter = mocker.MagicMock(return_value = 10000)

        result = _convert_to_qtd("curr_stub", None, Quarter.Q1, mock_getter)

        assert result == 10000
        mock_getter.assert_called_once_with("curr_stub")

    @pytest.mark.parametrize("quarter", [Quarter.Q2, Quarter.Q3, Quarter.Q4])
    @pytest.mark.parametrize("return_values", [[100,50],[100,50.5],[100,150],[100.5,150]])
    def test_return_calculated_qtd_when_q2_to_q4(self, mocker,quarter, return_values):
        #Q2-Q4일 때 -> curr - prior QTD 계산 정확도
        current_ytd, prior_ytd = return_values
        expected_qtd = current_ytd - prior_ytd

        mock_getter = mocker.MagicMock(side_effect=[current_ytd, prior_ytd])

        result = _convert_to_qtd("curr_stub", "prior_stub", quarter,mock_getter)

        # float 연산 정밀도 문제를 방지하기 위해 pytest.approx 사용
        assert result == pytest.approx(expected_qtd)
        assert mock_getter.call_count == 2
        mock_getter.assert_has_calls([
            mocker.call("curr_stub"),
            mocker.call("prior_stub"),
        ])

    def test_return_none_when_prior_ytd_is_none_at_q2_to_q4(self, mocker):
        #prior_ytd가 None이면 -> None 반환
        mock_getter = mocker.MagicMock(side_effect=[3000, None])

        result = _convert_to_qtd("curr_stub", "prior_stub", Quarter.Q3, mock_getter)

        assert result is None
        assert mock_getter.call_count == 2
        mock_getter.assert_has_calls([
            mocker.call("curr_stub"),
            mocker.call("prior_stub")
        ])

    def test_return_none_when_current_ytd_is_none(self, mocker):
        #current_ytd가 None이면 -> None 반환
        mock_getter = mocker.MagicMock(return_value=None)
        
        result = _convert_to_qtd("curr_stub", "prior_stub", Quarter.Q2, mock_getter)
        
        assert result is None
        mock_getter.assert_called_once_with("curr_stub")


"""
_determine_quarter(filing: Filing) -> Quarter:
mocking: _determine_quarter_from_months, filing

정상1. filing 정상  -> Q1,Q2,Q3,Q4 중 return
    - Q1,2,3,4 판별 확인은 통합 테스트 대상
2. form 없음 → None return/헬퍼 함수 assert_not_called()
3. fiscal_year_end 없음 → None return/헬퍼 함수 assert_not_called()
4. period_of_report 없음 → None return/헬퍼 함수 assert_not_called()
5. Edgartools 요청중 Exception 발생 → None return/헬퍼 함수 assert_not_called()
"""
class TestDetermineQuarter:
    #form: str | None, fiscal_year_end: str | None, period_of_report: str | None

    def test_return_quarter_when_filing_is_valid(self, mocker, create_filing):
        #정상1. filing 정상  -> Q1,Q2,Q3,Q4 중 하나의 경우만
        mock_filing = create_filing(
            form="10-Q",fiscal_year_end="1231",period_of_report="2023-06-30"
        )
        mock_helper = mocker.patch(
            MODULE_PATH+"._determine_quarter_from_months",
            return_value=Quarter.Q2
        )

        result = _determine_quarter(mock_filing)

        assert result == Quarter.Q2
        mock_helper.assert_called_once_with("10-Q", "1231","2023-06-30")

    def test_return_none_when_form_is_none(self,create_filing, mocker):
        #2. form 없음 → None return/헬퍼 함수 assert_not_called()
        mock_filing = create_filing(
            form=None, 
            fiscal_year_end="1231", 
            period_of_report="2023-06-30"
        )
        mock_helper = mocker.patch(
            MODULE_PATH + "._determine_quarter_from_months"
        )

        result = _determine_quarter(mock_filing)

        assert result is None
        mock_helper.assert_not_called()

    def test_return_none_when_fiscal_year_end_is_none(self, create_filing, mocker):
        # 3. fiscal_year_end 없음 → None return/헬퍼 함수 assert_not_called()
        mock_filing = create_filing(
            form="10-Q",
            fiscal_year_end=None,
            period_of_report="2023-06-30"
        )
        mock_helper = mocker.patch(MODULE_PATH + "._determine_quarter_from_months")

        result = _determine_quarter(mock_filing)

        assert result is None
        mock_helper.assert_not_called()

    def test_return_none_when_period_of_report_is_none(self, create_filing, mocker):
        # 4. period_of_report 없음 → None return/헬퍼 함수 assert_not_called()
        mock_filing = create_filing(
            form="10-Q",
            fiscal_year_end="1231",
            period_of_report=None
        )
        mock_helper = mocker.patch(MODULE_PATH + "._determine_quarter_from_months")

        result = _determine_quarter(mock_filing)

        assert result is None
        mock_helper.assert_not_called()

    def test_return_none_when_edgartools_raises_exception(self, create_filing, mocker):
        # 5. Edgartools 요청중 Exception 발생 → None return/헬퍼 함수 assert_not_called()
        mock_filing = create_filing(
            form="10-Q",
            fiscal_year_end="1231",
            period_of_report="2023-06-30"
        )
        type(mock_filing).company = mocker.PropertyMock(side_effect=Exception("Edgartools error"))
        mock_helper = mocker.patch(MODULE_PATH + "._determine_quarter_from_months")

        result = _determine_quarter(mock_filing)

        assert result is None
        mock_helper.assert_not_called()

"""
def _determine_quarter_from_months(form: str | None, fiscal_year_end: str | None, period_of_report: str | None) -> Quarter | None:
mocking: _extract_month

1. fiscal_end_month is None -> None return
2. report_month is None -> None return
3. month_diff가 _QUARTER_MONTH_DIFF_MAP에 없는 값 -> None return
정상 4. 인자가 정상 -> Q1,Q2,Q3 return
정상 4-1. Q1 return
정상 4-2. Q2 return
정상 4-3. Q3 return
정상 4-4. ("10-K", "10-K/A") -> Q4 return
"""
class TestDetermineQuarterFromMonths:
    
    @pytest.fixture
    def create_extract_month(self, mocker):
        def _factory(fiscal_end_month: int | None, report_month: int | None):
            return mocker.patch(
                MODULE_PATH + "._extract_month",
                side_effect=[fiscal_end_month, report_month]
            )
        return _factory

    def test_return_none_when_fiscal_end_month_is_none(self, create_extract_month):
        # 1. fiscal_end_month is None -> None return
        create_extract_month(fiscal_end_month=None, report_month=6)

        result = _determine_quarter_from_months("10-Q", "dummy", "dummy")

        assert result is None

    def test_return_none_when_report_month_is_none(self, create_extract_month):
        # 2. report_month is None -> None return
        create_extract_month(fiscal_end_month=12, report_month=None)

        result = _determine_quarter_from_months("10-Q", "dummy", "dummy")

        assert result is None

    def test_return_none_when_month_diff_not_in_map(self, create_extract_month):
        # 3. month_diff가 _QUARTER_MONTH_DIFF_MAP에 없는 값 -> None return
        # diff = (12 - 12) % 12 = 0 → 맵에 없음
        create_extract_month(fiscal_end_month=12, report_month=12)

        result = _determine_quarter_from_months("10-Q", "dummy", "dummy")

        assert result is None

    @pytest.mark.parametrize("fiscal_end_month, report_month, expected", [
        (12, 3, Quarter.Q1),   # diff=9
        (12, 6, Quarter.Q2),   # diff=6
        (12, 9, Quarter.Q3),   # diff=3
    ])
    def test_return_quarter_when_args_are_valid(
        self, create_extract_month, fiscal_end_month, report_month, expected
    ):
        # 정상4. 인자가 정상 -> Q1,Q2,Q3 return
        create_extract_month(fiscal_end_month=fiscal_end_month, report_month=report_month)

        result = _determine_quarter_from_months("10-Q", "dummy", "dummy")

        assert result == expected

    @pytest.mark.parametrize("form", ["10-K", "10-K/A"])
    def test_return_q4_when_form_is_10k(self, mocker, form):
        # 정상4-4. ("10-K", "10-K/A") -> Q4 return
        mock_extract = mocker.patch(MODULE_PATH + "._extract_month")

        result = _determine_quarter_from_months(form, "dummy", "dummy")

        assert result == Quarter.Q4
        mock_extract.assert_not_called()

"""
def _extract_month(date_str: str | None, value_name: str) -> int | None:
mocking: 없음

1. date_str 없음 -> None return
2. value_name이 fiscal_year_end,period_of_report 중 하나가 아님 -> None return
3. date_str을 integer로 변환 불가 -> None return
4. month가 1-12사이의 값이 아님 -> None return
5. date_str 길이가 비정상인 경우 -> None return
정상 6. fiscal_year_end와 정상 date_str -> month return
정상 7. period_of_report과 정상 date_str -> month return
"""
class TestExtractMonth:

    @pytest.mark.parametrize("value_name", ["fiscal_year_end", "period_of_report"])
    def test_return_none_when_date_str_is_none(self, value_name):
        # 1. date_str 없음 -> None return
        result = _extract_month(None, value_name)

        assert result is None

    def test_return_none_when_value_name_is_unknown(self):
        # 2. value_name이 fiscal_year_end, period_of_report 중 하나가 아님 -> None return
        result = _extract_month("1231", "unknown")

        assert result is None

    @pytest.mark.parametrize("date_str, value_name", [
        ("AB31", "fiscal_year_end"),       # int 변환 불가
        ("2023-AB-30", "period_of_report"), # int 변환 불가
    ])
    def test_return_none_when_date_str_is_not_integer(self, date_str, value_name):
        # 3. date_str을 integer로 변환 불가 -> None return
        result = _extract_month(date_str, value_name)

        assert result is None

    @pytest.mark.parametrize("date_str, value_name", [
        ("0031", "fiscal_year_end"),       # month=00 → 범위 밖
        ("2023-13-30", "period_of_report"), # month=13 → 범위 밖
    ])
    def test_return_none_when_month_is_out_of_range(self, date_str, value_name):
        # 4. month가 1-12사이의 값이 아님 -> None return
        result = _extract_month(date_str, value_name)

        assert result is None

    @pytest.mark.parametrize("date_str, value_name", [
        ("12", "fiscal_year_end"),       # len=2, expected=4
        ("03", "fiscal_year_end"),       # len=2, expected=4
        ("2023-06", "period_of_report"), # len=7, expected=10
    ])
    def test_return_none_when_date_str_length_is_invalid(self, date_str, value_name):
        # 5. date_str 길이가 비정상인 경우 -> None return
        result = _extract_month(date_str, value_name)

        assert result is None

    def test_return_month_when_fiscal_year_end_is_valid(self):
        # 정상6. fiscal_year_end와 정상 date_str -> month return
        result = _extract_month("1231", "fiscal_year_end")

        assert result == 12

    def test_return_month_when_period_of_report_is_valid(self):
        # 정상7. period_of_report과 정상 date_str -> month return
        result = _extract_month("2023-06-30", "period_of_report")

        assert result == 6


"""
_select_most_recent_filing
1. filtered_candidate_filings가 None -> None return
2. filtered_candidate_filings가 empyt list -> None return
정상 3. filtered_candidate_filings가 1개 이상 -> 직전 분기 공시 return
3.1 1개 -> 정상 return 되는지 확인
3.2 2개 -> 정상 return
3.3 5개 -> 가장 적절한 Filing return
4. filing_date가 동일한 공시가 2개 있을 때 (인덱스 0, 1) -> 인덱스 0의 filing return
   (latest()가 최신순 정렬이므로 인덱스 0이 실제로 더 나중에 처리된 filing)
"""
class TestSelectMostRecentFiling:
    def test_return_none_when_candidate_filings_are_none(self):
        #1. filtered_candidate_filings가 None -> None return
        filtered_candidate_filings = None

        result = _select_most_recent_filing(filtered_candidate_filings)

        assert result is None

    def test_return_none_when_candidate_filings_are_empty_list(self):
        #2. filtered_candidate_filings가 empyt list -> None return
        filtered_candidate_filings = []

        result = _select_most_recent_filing(filtered_candidate_filings)

        assert result is None

    def test_return_valid_filing_when_len_of_candidate_filings_is_one(self, create_filing):
        #정상 3. filtered_candidate_filings가 1개 이상 -> 직전 분기 공시 return
        #3.1 1개 -> 정상 return 되는지 확인
        mock_filing = create_filing(filing_date="2022-11-15")
        filtered_candidate_filings = [mock_filing]

        result = _select_most_recent_filing(filtered_candidate_filings)

        assert result == mock_filing
        assert result.filing_date == "2022-11-15"

    def test_return_most_recent_filing_when_len_of_candidate_filings_is_two(self, create_filing):
        #3.2 2개 -> 정상 return
        older_filing = create_filing(filing_date="2022-11-15")
        newer_filing = create_filing(filing_date="2022-12-01")
        filtered_candidate_filings = [older_filing, newer_filing]

        result = _select_most_recent_filing(filtered_candidate_filings)

        assert result == newer_filing
        assert result.filing_date == "2022-12-01"

    def test_return_most_recent_filing_when_len_of_candidate_filings_is_five(self, create_filing):
        #3.3 5개 -> 가장 적절한 Filing return
        filing_1 = create_filing(filing_date="2022-08-10")
        filing_2 = create_filing(filing_date="2022-11-15")
        filing_3 = create_filing(filing_date="2022-09-30")
        filing_4 = create_filing(filing_date="2022-12-01")
        filing_5 = create_filing(filing_date="2022-10-20")
        filtered_candidate_filings = [filing_1, filing_2, filing_3, filing_4, filing_5]

        result = _select_most_recent_filing(filtered_candidate_filings)

        assert result == filing_4
        assert result.filing_date == "2022-12-01"

    def test_return_first_index_filing_when_two_filings_have_same_date(self, create_filing):
        #4. filing_date가 동일한 공시가 2개 있을 때 (인덱스 0, 1) -> 인덱스 0의 filing return
        #   (latest()가 최신순 정렬이므로 인덱스 0이 실제로 더 나중에 처리된 filing)
        filing_index_0 = create_filing(filing_date="2022-11-15")
        filing_index_1 = create_filing(filing_date="2022-11-15")
        filtered_candidate_filings = [filing_index_0, filing_index_1]

        result = _select_most_recent_filing(filtered_candidate_filings)

        assert result == filing_index_0
        assert result.filing_date == "2022-11-15"
        

"""
_filter_candidate_filings_by_quarter_offset
1. current month가 None -> None return
정상 2. 후보 filing중에 offest==PRIOR_QUARTER_OFFSET인 공시가 없음 -> empty list return
정상 3. 후보 filing중에 직전분기 공시가 있음 -> matching_filing return
4. 후보 filing 중 n개의 candidate_month가 None일 경우 -> matching_filing에서 제외
5. candidate_filings가 empty list로 들어올 때 -> empty list return
6. 모든 후보의 candidate_month가 None일 때 -> empty list return (전체 제외)
"""
class TestFilterCandidateFilingsByQuarterOffset:
    def test_return_none_when_current_month_is_none(self,mocker, create_filing):
        #1. current month가 None -> None return
        current_month = None
        candidate_filings = [create_filing()]
        mock_extract_month = mocker.patch(
            MODULE_PATH+"._extract_month"
        )


        result = _filter_candidate_filings_by_quarter_offset(candidate_filings,current_month)

        assert result == None
        mock_extract_month.assert_not_called()

    def test_return_empty_list_when_no_filing_matches_prior_quarter_offset(self, mocker, create_filing):
        #정상 2. 후보 filing중에 offset==PRIOR_QUARTER_OFFSET인 공시가 없음 -> empty list return
        current_month = 11
        filing_1 = create_filing(period_of_report="2022-10-31")  # offset = (11-10)%12 = 1
        filing_2 = create_filing(period_of_report="2022-09-30")  # offset = (11-9)%12 = 2
        candidate_filings = [filing_1, filing_2]
        mock_extract_month = mocker.patch(
            MODULE_PATH+"._extract_month",
            side_effect=[10, 9]
        )

        result = _filter_candidate_filings_by_quarter_offset(candidate_filings, current_month)

        assert result == []
        assert mock_extract_month.call_count == 2
        mock_extract_month.assert_any_call("2022-10-31", "period_of_report")
        mock_extract_month.assert_any_call("2022-09-30", "period_of_report")

    def test_return_matching_filing_when_prior_quarter_filing_exists(self, mocker, create_filing):
        #정상 3. 후보 filing중에 직전분기 공시가 있음 -> matching_filing return
        current_month = 11
        matching = create_filing(period_of_report="2022-08-31")   # offset = (11-8)%12 = 3
        non_matching = create_filing(period_of_report="2022-10-31")  # offset = (11-10)%12 = 1
        candidate_filings = [matching, non_matching]
        mock_extract_month = mocker.patch(
            MODULE_PATH+"._extract_month",
            side_effect=[8, 10]
        )

        result = _filter_candidate_filings_by_quarter_offset(candidate_filings, current_month)

        assert result == [matching]
        assert mock_extract_month.call_count == 2
        mock_extract_month.assert_any_call("2022-08-31", "period_of_report")
        mock_extract_month.assert_any_call("2022-10-31", "period_of_report")

    def test_exclude_filings_when_candidate_month_is_none(self, mocker, create_filing):
        #4. 후보 filing 중 n개의 candidate_month가 None일 경우 -> matching_filing에서 제외
        current_month = 11
        valid_filing = create_filing(period_of_report="2022-08-31")  # offset = (11-8)%12 = 3
        none_filing_1 = create_filing(period_of_report=None)
        none_filing_2 = create_filing(period_of_report=None)
        candidate_filings = [valid_filing, none_filing_1, none_filing_2]
        mock_extract_month = mocker.patch(
            MODULE_PATH+"._extract_month",
            side_effect=[8, None, None]
        )

        result = _filter_candidate_filings_by_quarter_offset(candidate_filings, current_month)

        assert result == [valid_filing]
        assert mock_extract_month.call_count == 3
        mock_extract_month.assert_any_call("2022-08-31", "period_of_report")
        mock_extract_month.assert_any_call(None, "period_of_report")

    def test_return_empty_list_when_all_candidate_months_are_none(self, mocker, create_filing):
        #6. 모든 후보의 candidate_month가 None일 때 -> empty list return (전체 제외)
        current_month = 11
        filing_1 = create_filing(period_of_report=None)
        filing_2 = create_filing(period_of_report=None)
        candidate_filings = [filing_1, filing_2]
        mock_extract_month = mocker.patch(
            MODULE_PATH+"._extract_month",
            side_effect=[None, None]
        )

        result = _filter_candidate_filings_by_quarter_offset(candidate_filings, current_month)

        assert result == []
        assert mock_extract_month.call_count == 2
        mock_extract_month.assert_any_call(None, "period_of_report")

"""
_find_prior_filing_candidates(getfiling.latest: 0->N이면 최신->과거)
1. company가 None -> None return
2. filing_date가 None -> None return
3. edgartools에서 예외 발생 -> Exception 발생 -> None return
4. filing_date가 YYYY-mm-dd형식이 아닐 경우(예 MM/DD/YYYY) -> Exception 발생 -> None return
정상 5. get_filing 조건에 맞는 공시가 하나도 없을 때 -> empty list return
정상 6. get_filing 조건에 맞는 공시가 3개 있을 때 -> len==3인 list return
정상 7. get_filing 조건에 맞는 공시가 6개 있을 때 0> len==6인 list return
정상 8. get_filing 조건에 맞는 공시가 1개 있을 때 0> len==1인 list return
    **candidate_filing[0]이 Filing type 객체가 맞는지 확인 필요 
"""
class TestFindPriorFilingCandidates:
    def test_return_none_when_company_is_none(self):
        #1. company가 None -> None return
        company = None
        filing_date = "2022-11-15"

        result = _find_prior_filing_candidates(company, filing_date)

        assert result is None

    def test_return_none_when_filing_date_is_none(self, mocker):
        #2. filing_date가 None -> None return
        mock_company = mocker.MagicMock(spec=Company)
        filing_date = None

        result = _find_prior_filing_candidates(mock_company, filing_date)

        assert result is None

    def test_return_none_when_edgartools_raises_exception(self, mocker):
        #3. edgartools에서 예외 발생 -> Exception 발생 -> None return
        mock_company = mocker.MagicMock(spec=Company)
        mock_company.get_filings.side_effect = Exception("unexpected error")
        filing_date = "2022-11-15"

        result = _find_prior_filing_candidates(mock_company, filing_date)

        assert result is None

    def test_return_none_when_filing_date_format_is_invalid(self, mocker):
        #4. filing_date가 YYYY-mm-dd형식이 아닐 경우(예 MM/DD/YYYY) -> Exception 발생 -> None return
        mock_company = mocker.MagicMock(spec=Company)
        mock_company.get_filings.side_effect = Exception("invalid date format")
        filing_date = "11/15/2022"

        result = _find_prior_filing_candidates(mock_company, filing_date)

        assert result is None

    def test_return_empty_list_when_no_filing_exists(self, mocker):
        #정상 5. get_filing 조건에 맞는 공시가 하나도 없을 때 -> empty list return
        mock_company = mocker.MagicMock(spec=Company)
        mock_company.get_filings.return_value.latest.return_value = []
        filing_date = "2022-11-15"

        result = _find_prior_filing_candidates(mock_company, filing_date)

        assert result == []
        mock_company.get_filings.assert_called_once_with(
            form="10-Q",
            amendments=True,
            filing_date=f":{filing_date}"
        )
        mock_company.get_filings.return_value.latest.assert_called_once_with(6)

    def test_return_list_when_three_filings_exist(self, mocker):
        #정상 6. get_filing 조건에 맞는 공시가 3개 있을 때 -> len==3인 list return
        mock_company = mocker.MagicMock(spec=Company)
        mock_filings = [mocker.MagicMock(spec=Filing) for _ in range(3)]
        mock_company.get_filings.return_value.latest.return_value = mock_filings
        filing_date = "2022-11-15"

        result = _find_prior_filing_candidates(mock_company, filing_date)

        assert len(result) == 3
        mock_company.get_filings.assert_called_once_with(
            form="10-Q",
            amendments=True,
            filing_date=f":{filing_date}"
        )
        mock_company.get_filings.return_value.latest.assert_called_once_with(6)

    def test_return_list_when_six_filings_exist(self, mocker):
        #정상 7. get_filing 조건에 맞는 공시가 6개 있을 때 -> len==6인 list return
        mock_company = mocker.MagicMock(spec=Company)
        mock_filings = [mocker.MagicMock(spec=Filing) for _ in range(6)]
        mock_company.get_filings.return_value.latest.return_value = mock_filings
        filing_date = "2022-11-15"

        result = _find_prior_filing_candidates(mock_company, filing_date)

        assert len(result) == 6
        mock_company.get_filings.assert_called_once_with(
            form="10-Q",
            amendments=True,
            filing_date=f":{filing_date}"
        )
        mock_company.get_filings.return_value.latest.assert_called_once_with(6)

    def test_return_list_when_one_filing_exists(self, mocker):
        #정상 8. get_filing 조건에 맞는 공시가 1개 있을 때 -> len==1인 list return
        #        candidate_filing[0]이 Filing type 객체가 맞는지 확인
        mock_company = mocker.MagicMock(spec=Company)
        mock_filing = mocker.MagicMock(spec=Filing)
        mock_company.get_filings.return_value.latest.return_value = [mock_filing]
        filing_date = "2022-11-15"

        result = _find_prior_filing_candidates(mock_company, filing_date)

        assert len(result) == 1
        result[0] is mock_filing
        mock_company.get_filings.assert_called_once_with(
            form="10-Q",
            amendments=True,
            filing_date=f":{filing_date}"
        )
        mock_company.get_filings.return_value.latest.assert_called_once_with(6)

"""
_find_prior_period_filing
1. _find_prior_filing_candidates에서 None return -> None return
    _filter_candidate_filings_by_quarter_offset,_select_most_recent_filing 미호출
2. _find_prior_filing_candidates에서 empty list return -> None return
    _filter_candidate_filings_by_quarter_offset,_select_most_recent_filing 미호출
3. _filter_candidate_filings_by_quarter_offset에서 None return -> None return
    _select_most_recent_filing 미호출
4. _filter_candidate_filings_by_quarter_offset에서 empty list return -> None return
    _select_most_recent_filing 미호출
5. current_filing의 직전 분기에 해당하는 공시 없음 -> None return
    _find_prior_filing_candidates, _filter_candidate_filings_by_quarter_offset 호출됨
    _select_most_recent_filing 미호출
6. current_filing의 직전 분기에 해당하는 공시 존재 -> 해당 prior filing return
    _find_prior_filing_candidates, _filter_candidate_filings_by_quarter_offset, _select_most_recent_filing 모두 호출됨
7. _find_prior_period_filing이 _find_prior_filing_candidates 호출 시
   current_filing.company와 current_filing.filing_date를 정확히 전달하는지 확인
8. _find_prior_period_filing이 _filter_candidate_filings_by_quarter_offset 호출 시
   candidate_filings와 current_filing_report_month를 정확히 전달하는지 확인
"""
class TestFindPriorPeriodFiling:
    def test_return_none_when_find_prior_filing_candidates_returns_none(self, mocker, create_filing):
        #1. _find_prior_filing_candidates에서 None return -> None return
        #   _filter_candidate_filings_by_quarter_offset, _select_most_recent_filing 미호출
        mock_current_filing = create_filing(filing_date="2022-11-15")
        current_filing_report_month = 9

        mock_find_candidates = mocker.patch(MODULE_PATH+"._find_prior_filing_candidates", return_value=None)
        mock_filter = mocker.patch(MODULE_PATH+"._filter_candidate_filings_by_quarter_offset")
        mock_select = mocker.patch(MODULE_PATH+"._select_most_recent_filing")

        result = _find_prior_period_filing(mock_current_filing, current_filing_report_month)

        assert result is None
        mock_filter.assert_not_called()
        mock_select.assert_not_called()

    def test_return_none_when_find_prior_filing_candidates_returns_empty_list(self, mocker, create_filing):
        #2. _find_prior_filing_candidates에서 empty list return -> None return
        #   _filter_candidate_filings_by_quarter_offset, _select_most_recent_filing 미호출
        mock_current_filing = create_filing(filing_date="2022-11-15")
        current_filing_report_month = 9

        mock_find_candidates = mocker.patch(MODULE_PATH+"._find_prior_filing_candidates", return_value=[])
        mock_filter = mocker.patch(MODULE_PATH+"._filter_candidate_filings_by_quarter_offset")
        mock_select = mocker.patch(MODULE_PATH+"._select_most_recent_filing")

        result = _find_prior_period_filing(mock_current_filing, current_filing_report_month)

        assert result is None
        mock_filter.assert_not_called()
        mock_select.assert_not_called()

    def test_return_none_when_filter_returns_none(self, mocker, create_filing):
        #3. _filter_candidate_filings_by_quarter_offset에서 None return -> None return
        #   _select_most_recent_filing 미호출
        mock_current_filing = create_filing(filing_date="2022-11-15")
        current_filing_report_month = 9
        mock_candidates = [create_filing()]

        mocker.patch(MODULE_PATH+"._find_prior_filing_candidates", return_value=mock_candidates)
        mock_filter = mocker.patch(MODULE_PATH+"._filter_candidate_filings_by_quarter_offset", return_value=None)
        mock_select = mocker.patch(MODULE_PATH+"._select_most_recent_filing")

        result = _find_prior_period_filing(mock_current_filing, current_filing_report_month)

        assert result is None
        mock_select.assert_not_called()

    def test_return_none_when_filter_returns_empty_list(self, mocker, create_filing):
        #4. _filter_candidate_filings_by_quarter_offset에서 empty list return -> None return
        #   _select_most_recent_filing 미호출
        mock_current_filing = create_filing(filing_date="2022-11-15")
        current_filing_report_month = 9
        mock_candidates = [create_filing()]

        mocker.patch(MODULE_PATH+"._find_prior_filing_candidates", return_value=mock_candidates)
        mock_filter = mocker.patch(MODULE_PATH+"._filter_candidate_filings_by_quarter_offset", return_value=[])
        mock_select = mocker.patch(MODULE_PATH+"._select_most_recent_filing")

        result = _find_prior_period_filing(mock_current_filing, current_filing_report_month)

        assert result is None
        mock_select.assert_not_called()

    def test_return_none_when_no_prior_quarter_filing_exists(self, mocker, create_filing):
        #5. current_filing의 직전 분기에 해당하는 공시 없음 -> None return
        #   _find_prior_filing_candidates, _filter_candidate_filings_by_quarter_offset 호출됨
        #   _select_most_recent_filing 미호출
        mock_current_filing = create_filing(filing_date="2022-11-15")
        current_filing_report_month = 9
        mock_candidates = [create_filing()]

        mock_find_candidates = mocker.patch(MODULE_PATH+"._find_prior_filing_candidates", return_value=mock_candidates)
        mock_filter = mocker.patch(MODULE_PATH+"._filter_candidate_filings_by_quarter_offset", return_value=[])
        mock_select = mocker.patch(MODULE_PATH+"._select_most_recent_filing")

        result = _find_prior_period_filing(mock_current_filing, current_filing_report_month)

        assert result is None
        mock_find_candidates.assert_called_once()
        mock_filter.assert_called_once()
        mock_select.assert_not_called()

    def test_return_prior_filing_when_prior_quarter_filing_exists(self, mocker, create_filing):
        #6. current_filing의 직전 분기에 해당하는 공시 존재 -> 해당 prior filing return
        #   _find_prior_filing_candidates, _filter_candidate_filings_by_quarter_offset, _select_most_recent_filing 모두 호출됨
        mock_current_filing = create_filing(filing_date="2022-11-15")
        current_filing_report_month = 9
        mock_candidates = [create_filing()]
        mock_filtered = [create_filing()]
        mock_prior_filing = create_filing(filing_date="2022-08-15")

        mock_find_candidates = mocker.patch(MODULE_PATH+"._find_prior_filing_candidates", return_value=mock_candidates)
        mock_filter = mocker.patch(MODULE_PATH+"._filter_candidate_filings_by_quarter_offset", return_value=mock_filtered)
        mock_select = mocker.patch(MODULE_PATH+"._select_most_recent_filing", return_value=mock_prior_filing)

        result = _find_prior_period_filing(mock_current_filing, current_filing_report_month)

        assert result == mock_prior_filing
        mock_find_candidates.assert_called_once()
        mock_filter.assert_called_once()
        mock_select.assert_called_once()

    def test_find_prior_filing_candidates_receives_correct_args(self, mocker, create_filing):
        #7. _find_prior_period_filing이 _find_prior_filing_candidates 호출 시
        #   current_filing.company와 current_filing.filing_date를 정확히 전달하는지 확인
        mock_current_filing = create_filing(filing_date="2022-11-15")
        current_filing_report_month = 9

        mock_find_candidates = mocker.patch(MODULE_PATH+"._find_prior_filing_candidates", return_value=None)
        mocker.patch(MODULE_PATH+"._filter_candidate_filings_by_quarter_offset")
        mocker.patch(MODULE_PATH+"._select_most_recent_filing")

        _find_prior_period_filing(mock_current_filing, current_filing_report_month)

        mock_find_candidates.assert_called_once_with(
            mock_current_filing.company,
            mock_current_filing.filing_date
        )

    def test_filter_candidate_filings_receives_correct_args(self, mocker, create_filing):
        #8. _find_prior_period_filing이 _filter_candidate_filings_by_quarter_offset 호출 시
        #   candidate_filings와 current_filing_report_month를 정확히 전달하는지 확인
        mock_current_filing = create_filing(filing_date="2022-11-15")
        current_filing_report_month = 9
        mock_candidates = [create_filing()]

        mocker.patch(MODULE_PATH+"._find_prior_filing_candidates", return_value=mock_candidates)
        mock_filter = mocker.patch(MODULE_PATH+"._filter_candidate_filings_by_quarter_offset", return_value=None)
        mocker.patch(MODULE_PATH+"._select_most_recent_filing")

        _find_prior_period_filing(mock_current_filing, current_filing_report_month)

        mock_filter.assert_called_once_with(
            mock_candidates,
            current_filing_report_month
        )


"""
_get_financials
정상1. current_quarter가 Q1일 경우 -> (current,none) return
정상2. Q2,3,4일 경우 -> (current,prior) return
3. prior_filing이 None인 경우 -> (None,None) return
4. prior_financials가 None인 경우 -> (None,None) return
"""
class TestGetFinancials:
    def test_return_current_and_none_when_current_quarter_is_q1(self, mocker, create_filing):
        #정상1. current_quarter가 Q1일 경우 -> (current,none) return
        mock_filing = create_filing()
        stub_current_quarter = Quarter.Q1
        stub_financials = mocker.MagicMock(spec=Financials)
        mock_filing.obj.return_value.financials = stub_financials

        mock_find_prior_filing = mocker.patch(
            MODULE_PATH+"._find_prior_period_filing"
        )

        result = _get_financials(mock_filing, stub_current_quarter)

        assert result == (stub_financials, None)
        mock_find_prior_filing.assert_not_called()

    def test_return_current_and_prior_when_quarter_is_not_q1(self, mocker, create_filing):
        #정상2. Q2,3,4일 경우 -> (current,prior) return
        mock_filing = create_filing(period_of_report="2022-12-30")
        stub_current_quarter = Quarter.Q2
        stub_current_financials = mocker.MagicMock(spec=Financials)
        stub_prior_financials = mocker.MagicMock(spec=Financials)
        mock_filing.obj.return_value.financials = stub_current_financials

        mock_prior_filing = mocker.MagicMock(spec=Filing)
        mock_prior_filing.obj.return_value.financials = stub_prior_financials
        mock_find_prior_filing = mocker.patch(
            MODULE_PATH + "._find_prior_period_filing",
            return_value=mock_prior_filing
        )

        result = _get_financials(mock_filing, stub_current_quarter)

        mock_find_prior_filing.assert_called_once_with(mock_filing, mock_filing.period_of_report)
        assert result == (stub_current_financials, stub_prior_financials)


    def test_return_none_none_when_prior_filing_is_none(self, mocker, create_filing):
        #3. prior_filing이 None인 경우 -> (None,None) return
        mock_filing = create_filing(period_of_report="2022-12-30")
        stub_current_quarter = Quarter.Q2
        mock_filing.obj.return_value.financials = mocker.MagicMock(spec=Financials)

        mock_find_prior_filing = mocker.patch(
            MODULE_PATH + "._find_prior_period_filing",
            return_value=None
        )

        result = _get_financials(mock_filing, stub_current_quarter)

        mock_find_prior_filing.assert_called_once_with(mock_filing, mock_filing.period_of_report)
        assert result == (None, None)


    def test_return_none_none_when_prior_financials_is_none(self, mocker, create_filing):
        #4. prior_financials가 None인 경우 -> (None,None) return
        mock_filing = create_filing(period_of_report="2022-12-30")
        stub_current_quarter = Quarter.Q2
        mock_filing.obj.return_value.financials = mocker.MagicMock(spec=Financials)

        mock_prior_filing = mocker.MagicMock(spec=Filing)
        mock_prior_filing.obj.return_value.financials = None
        mock_find_prior_filing = mocker.patch(
            MODULE_PATH + "._find_prior_period_filing",
            return_value=mock_prior_filing
        )

        result = _get_financials(mock_filing, stub_current_quarter)

        mock_find_prior_filing.assert_called_once_with(mock_filing, mock_filing.period_of_report)
        assert result == (None, None)

"""
get_items_qtd_cash_flow_statement
1. current_filing이 None -> None return
2. current_quarter가 None -> None return
3. current_financials과 prior_financials 둘다 None -> None return
정상4. valid args -> dict return
정상4.1 get_operating_cash_flow() 한개 -> ocf한개 return
정상4.2 get_capital_expenditures(),get_operating_cash_flow() 2개 -> ocf,capex 2개 return
정상4.3 get_free_cash_flow(),get_capital_expenditures(),get_operating_cash_flow() 3개 -> ocf,capex,fcf 3s개 return
정상5. current_quarter가 Q1 -> prior_financials=None인 채로 dict 정상 return
       (values 안에서 _convert_to_qtd가 prior=None으로 호출되는지 확인)
"""
class TestGetItemsQtdCashFlowStatement:
    def test_return_none_when_current_filing_is_none(self):
        # 1. current_filing이 None -> None return
        result = get_items_qtd_cash_flow_statement(None, {})

        assert result is None

    def test_return_none_when_current_quarter_is_none(self, mocker, create_filing):
        # 2. current_quarter가 None -> None return
        mock_filing = create_filing()
        mock_helper = mocker.patch(MODULE_PATH + "._determine_quarter", return_value=None)
        mock_get_financials = mocker.patch(MODULE_PATH + "._get_financials") 

        result = get_items_qtd_cash_flow_statement(mock_filing, {})
        mock_helper.assert_called_once_with(mock_filing)
        mock_get_financials.assert_not_called()
        assert result is None

    def test_return_none_when_both_financials_are_none(self, mocker, create_filing):
        # 3. current_financials과 prior_financials 둘다 None -> None return
        mock_filing = create_filing()
        mock_determine_quarter = mocker.patch(MODULE_PATH + "._determine_quarter", return_value=Quarter.Q2)
        mock_get_financials = mocker.patch(MODULE_PATH + "._get_financials", return_value=(None, None))

        result = get_items_qtd_cash_flow_statement(mock_filing, {})

        #then
        mock_determine_quarter.assert_called_once_with(mock_filing)
        mock_get_financials.assert_called_once_with(mock_filing, Quarter.Q2)

        assert result is None

    def test_return_dict_with_one_concept(self, mocker, create_filing):
        # 정상4.1 get_operating_cash_flow() 한개 -> ocf한개 return
        mock_filing = create_filing()
        mock_determine_quarter = mocker.patch(MODULE_PATH + "._determine_quarter", return_value=Quarter.Q2)
        stub_current_financials = mocker.MagicMock(spec=Financials)
        stub_prior_financials = mocker.MagicMock(spec=Financials)
        mock_get_financials = mocker.patch(MODULE_PATH + "._get_financials", return_value=(stub_current_financials, stub_prior_financials))
        mock_convert_to_qtd = mocker.patch(MODULE_PATH + "._convert_to_qtd", return_value=100.0)

        concept_getters = {"operating_cash_flow": lambda f: f.get_operating_cash_flow()}
        result = get_items_qtd_cash_flow_statement(mock_filing, concept_getters)

        #then
        mock_determine_quarter.assert_called_once_with(mock_filing)
        mock_get_financials.assert_called_once_with(mock_filing, Quarter.Q2)

        assert mock_convert_to_qtd.call_count == 1
        assert result == {"quarter": Quarter.Q2, "values": {"operating_cash_flow": 100.0}}

    def test_return_dict_with_two_concepts(self, mocker, create_filing):
        # 정상4.2 get_capital_expenditures(),get_operating_cash_flow() 2개 -> ocf,capex 2개 return
        mock_filing = create_filing()
        mock_determine_quarter = mocker.patch(MODULE_PATH + "._determine_quarter", return_value=Quarter.Q2)
        stub_current_financials = mocker.MagicMock(spec=Financials)
        stub_prior_financials = mocker.MagicMock(spec=Financials)
        mock_get_financials = mocker.patch(MODULE_PATH + "._get_financials", return_value=(stub_current_financials, stub_prior_financials))
        mock_convert_to_qtd =mocker.patch(MODULE_PATH + "._convert_to_qtd", side_effect=[100.0, 200.0])

        concept_getters = {
            "operating_cash_flow": lambda f: f.get_operating_cash_flow(),
            "capital_expenditures": lambda f: f.get_capital_expenditures(),
        }
        result = get_items_qtd_cash_flow_statement(mock_filing, concept_getters)

        #then
        mock_determine_quarter.assert_called_once_with(mock_filing)
        mock_get_financials.assert_called_once_with(mock_filing, Quarter.Q2)
        assert mock_convert_to_qtd.call_count == 2
        assert result == {
            "quarter": Quarter.Q2,
            "values": {
                "operating_cash_flow": 100.0,
                "capital_expenditures": 200.0,
            }
        }

    def test_return_dict_with_three_concepts(self, mocker, create_filing):
        # 정상4.3 get_free_cash_flow(),get_capital_expenditures(),get_operating_cash_flow() 3개 -> ocf,capex,fcf 3개 return
        mock_filing = create_filing()
        mock_determine_quarter = mocker.patch(MODULE_PATH + "._determine_quarter", return_value=Quarter.Q2)
        stub_current_financials = mocker.MagicMock(spec=Financials)
        stub_prior_financials = mocker.MagicMock(spec=Financials)
        mock_get_financials = mocker.patch(MODULE_PATH + "._get_financials", return_value=(stub_current_financials, stub_prior_financials))
        mock_convert_to_qtd = mocker.patch(MODULE_PATH + "._convert_to_qtd", side_effect=[100.0, 200.0, 300.0])

        concept_getters = {
            "operating_cash_flow": lambda f: f.get_operating_cash_flow(),
            "capital_expenditures": lambda f: f.get_capital_expenditures(),
            "free_cash_flow": lambda f: f.get_free_cash_flow(),
        }
        result = get_items_qtd_cash_flow_statement(mock_filing, concept_getters)


        #then
        mock_determine_quarter.assert_called_once_with(mock_filing)
        mock_get_financials.assert_called_once_with(mock_filing, Quarter.Q2)
        assert mock_convert_to_qtd.call_count == 3
        assert result == {
            "quarter": Quarter.Q2,
            "values": {
                "operating_cash_flow": 100.0,
                "capital_expenditures": 200.0,
                "free_cash_flow": 300.0,
            }
        }

    def test_return_dict_with_prior_none_when_quarter_is_q1(self, mocker, create_filing):
        # 정상5. current_quarter가 Q1 -> prior_financials=None인 채로 dict 정상 return
        mock_filing = create_filing()
        mock_determine_quarter = mocker.patch(MODULE_PATH + "._determine_quarter", return_value=Quarter.Q1)
        stub_current_financials = mocker.MagicMock(spec=Financials)
        mock_get_financials = mocker.patch(MODULE_PATH + "._get_financials", return_value=(stub_current_financials, None))
        mock_convert_to_qtd = mocker.patch(MODULE_PATH + "._convert_to_qtd", return_value=100.0)

        concept_getters = {"operating_cash_flow": lambda f: f.get_operating_cash_flow()}
        result = get_items_qtd_cash_flow_statement(mock_filing, concept_getters)

        assert result == {"quarter": Quarter.Q1, "values": {"operating_cash_flow": 100.0}}
        mock_determine_quarter.assert_called_once_with(mock_filing)
        mock_get_financials.assert_called_once_with(mock_filing, Quarter.Q1)
        mock_convert_to_qtd.assert_called_once_with(stub_current_financials, None, Quarter.Q1, concept_getters["operating_cash_flow"])
"""
edgartools 단위 테스트 항목

4. _extract_quarter_from_filing 
    에러
    1. filing.period_of_report가 None/빈 문자열일 때 -> None 리턴
    2. period_str이 YYYY-mm-dd 형식이 아닐 때 -> None 리턴
    정상
    1. 정상 인자가 들어왔을 때 -> period_str에 따라 Enum Quarter
7. _get_cik_and_fiscal_year_end_via_edgartools
    에러
    1. company.get_filings() 결과가 비어있을 때 → None 리턴
    2. 잘못된 ticker -> Value Error -> None 리턴
    3. quarter_enum이 None일 때 -> None 리턴
    정상
    1. ticker가 올바르게 들어왔을 때 -> dict 리턴
"""

import pytest
from app.models.base import Quarter
from app.modules.company_sync.edgartools import (
    _extract_quarter_from_filing,
    get_cik_and_fiscal_year_end_via_edgartools
)


class TestExtractQuarterFromFiling:
    """_extract_quarter_from_filing 단위 테스트"""
    
    def test_extract_quarter_from_filing_with_none_period_returns_none(self, mocker):
        """에러1. filing.period_of_report가 None일 때 -> None 리턴"""
        # given-상황
        filing = mocker.Mock()
        filing.period_of_report = None
        
        # when-실행
        result = _extract_quarter_from_filing(filing)
        
        # then-결과 확인
        assert result is None
    
    def test_extract_quarter_from_filing_with_empty_period_returns_none(self, mocker):
        """에러1. filing.period_of_report가 빈 문자열일 때 -> None 리턴"""
        # given-상황
        filing = mocker.Mock()
        filing.period_of_report = ""
        
        # when-실행
        result = _extract_quarter_from_filing(filing)
        
        # then-결과 확인
        assert result is None
    
    def test_extract_quarter_from_filing_with_invalid_date_format_returns_none(self, mocker):
        """에러2. period_str이 YYYY-mm-dd 형식이 아닐 때 -> None 리턴"""
        # given-상황
        filing = mocker.Mock()
        filing.period_of_report = "2023/12/31"  # 잘못된 형식
        
        # when-실행
        result = _extract_quarter_from_filing(filing)
        
        # then-결과 확인
        assert result is None
    
    @pytest.mark.parametrize(
        "period_str,expected_quarter",
        [
            ("2023-01-31", Quarter.Q1),  # 1월 -> Q1
            ("2023-02-28", Quarter.Q1),  # 2월 -> Q1
            ("2023-03-31", Quarter.Q1),  # 3월 -> Q1
            ("2023-04-30", Quarter.Q2),  # 4월 -> Q2
            ("2023-05-31", Quarter.Q2),  # 5월 -> Q2
            ("2023-06-30", Quarter.Q2),  # 6월 -> Q2
            ("2023-07-31", Quarter.Q3),  # 7월 -> Q3
            ("2023-08-31", Quarter.Q3),  # 8월 -> Q3
            ("2023-09-30", Quarter.Q3),  # 9월 -> Q3
            ("2023-10-31", Quarter.Q4),  # 10월 -> Q4
            ("2023-11-30", Quarter.Q4),  # 11월 -> Q4
            ("2023-12-31", Quarter.Q4),  # 12월 -> Q4
        ]
    )
    def test_extract_quarter_from_filing_with_valid_date_returns_quarter_enum(self, mocker, period_str, expected_quarter):
        """정상1. 정상 인자가 들어왔을 때 -> period_str에 따라 Enum Quarter 리턴"""
        # given-상황
        filing = mocker.Mock()
        filing.period_of_report = period_str
        
        # when-실행
        result = _extract_quarter_from_filing(filing)
        
        # then-결과 확인
        assert result == expected_quarter
        assert isinstance(result, Quarter)


class TestGetCikAndFiscalYearEndViaEdgartools:
    """get_cik_and_fiscal_year_end_via_edgartools 단위 테스트"""
    
    def test_get_cik_and_fiscal_year_end_with_empty_filings_returns_none(self, mocker):
        """에러1. company.get_filings() 결과가 비어있을 때 → None 리턴"""
        # given-상황
        ticker = "AAPL"
        mock_company = mocker.Mock()
        mock_company.get_filings.return_value = []  # 빈 리스트
        
        mocker.patch(
            "app.modules.company_sync.edgartools.Company",
            return_value=mock_company
        )
        
        # when-실행
        result = get_cik_and_fiscal_year_end_via_edgartools(ticker)
        
        # then-결과 확인
        assert result is None
        mock_company.get_filings.assert_called_once_with(form="10-K")
    
    def test_get_cik_and_fiscal_year_end_with_invalid_ticker_returns_none(self, mocker):
        """에러2. 잘못된 ticker -> Value Error -> None 리턴"""
        # given-상황
        ticker = "INVALID_TICKER_12345"
        
        mock_company_class = mocker.patch(
            "app.modules.company_sync.edgartools.Company",
            side_effect=ValueError("Invalid ticker")
        )
        
        # when-실행
        result = get_cik_and_fiscal_year_end_via_edgartools(ticker)
        
        # then-결과 확인
        assert result is None
        mock_company_class.assert_called_once_with(ticker)
        
    
    def test_get_cik_and_fiscal_year_end_with_none_quarter_enum_returns_none(self, mocker):
        """에러3. quarter_enum이 None일 때 -> None 리턴"""
        # given-상황
        ticker = "AAPL"
        mock_filing = mocker.Mock()
        mock_filing.period_of_report = None  # quarter_enum이 None이 되게 함
        
        mock_filings = mocker.Mock()
        mock_filings.latest.return_value = mock_filing
        
        mock_company = mocker.Mock()
        mock_company.get_filings.return_value = mock_filings
        
        mocker.patch(
            "app.modules.company_sync.edgartools.Company",
            return_value=mock_company
        )
        
        # when-실행
        result = get_cik_and_fiscal_year_end_via_edgartools(ticker)
        
        # then-결과 확인
        assert result is None
    
    def test_get_cik_and_fiscal_year_end_with_valid_ticker_returns_dict(self, mocker):
        """정상1. ticker가 올바르게 들어왔을 때 -> dict 리턴"""
        # given-상황
        ticker = "AAPL"
        expected_cik = "0000320193"
        expected_quarter = Quarter.Q4
        
        mock_filing = mocker.Mock()
        mock_filing.period_of_report = "2023-12-31"  # Q4
        
        mock_filings = mocker.Mock()
        mock_filings.latest.return_value = mock_filing
        
        mock_company = mocker.Mock()
        mock_company.cik = expected_cik
        mock_company.get_filings.return_value = mock_filings
        
        mocker.patch(
            "app.modules.company_sync.edgartools.Company",
            return_value=mock_company
        )
        
        # when-실행
        result = get_cik_and_fiscal_year_end_via_edgartools(ticker)
        
        # then-결과 확인
        assert isinstance(result, dict)
        assert result["cik"] == expected_cik
        assert result["fiscal_year_end"] == expected_quarter
        assert set(result.keys()) == {"cik", "fiscal_year_end"}

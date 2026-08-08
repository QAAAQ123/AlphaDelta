"""
매출 QTD 계산 모듈 테스트

get_revenue_qtd(filing: Filing): 매출의 QTD 값을 리턴하는 getter

_extract_revenue_by_period_kind(filing: Filing, period_kind: str): 기간 종류에 따라 매출의 QTD를 계산하는 함수
정상1. QTD

_determine_period_kind(filing:Filing): QTD인지 YTD인지 확인하는 함수
정상1. days <= 120(QUARTER_MAX_DAYS)이면: "QTD" return
정상2. 120 < days <= 229(YTD_6M_MAX_DAYS)이면: "YTD6" return
정상3. 229 < days <= 329(YTD_9M_MAX_DAYS)이면: "YTD9" return
정상4. days > 329이면: period_type 또는 "unknown" return
예외1. days가 None이 포함된 경우: TypeError 발생
예외2. type="duration"인 period가 없는 경우: ValueError 발생
예외3. days가 None 단독인 경우: ValueError 발생
"""
from app.modules.financial_extractor.revenue import _determine_period_kind, get_revenue_qtd
from edgar import Filing
from unittest.mock import patch
import pytest

@pytest.fixture
def create_stub_filing(mocker):
    """
    mocker 픽스처를 활용해 Stub Filing 객체를 만들어주는 팩토리 픽스처입니다.
    """
    def _factory(period_of_report: str, reporting_periods: list):
        # spec=Filing으로 실제 edgartools 껍데기만 빌려옴 (실제 호출 X)
        stub_filing = mocker.MagicMock(spec=Filing)
        mock_xbrl = mocker.MagicMock()

        # 속성 및 return_value 설정
        mock_xbrl.period_of_report = period_of_report
        mock_xbrl.reporting_periods = reporting_periods
        stub_filing.xbrl.return_value = mock_xbrl

        return stub_filing

    return _factory

class TestDeterminePeriodKind:
    def test_determine_period_kind_return_QTD(self, create_stub_filing):
        """_determine_period_kind가 QTD를 정상 return하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 92
                },
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 273
                },
                {
                    "type": "duration",
                    "end_date": "2022-09-30",
                    "days": 92
                }
            ]
        )
        

        result = _determine_period_kind(stub_filing)

        assert result == "QTD"

    def test_determine_period_kind_return_YTD6(self, create_stub_filing):
        """_determine_period_kind가 YTD6를 정상 return하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 182,
                },
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 273
                },
                {
                    "type": "duration",
                    "end_date": "2022-09-30",
                    "days": 90
                }
            ]
        )

        result = _determine_period_kind(stub_filing)

        assert result == "YTD6"

    
    def test_determine_period_kind_return_YTD9(self, create_stub_filing):
        """_determine_period_kind가 YTD9를 정상 return하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 300,
                },
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 273
                },
                {
                    "type": "duration",
                    "end_date": "2022-09-30",
                    "days": 90
                }
            ]
        )

        result = _determine_period_kind(stub_filing)

        assert result == "YTD9"

    def test_determine_period_kind_return_period_type(self, create_stub_filing):
        """days > YTD_9M_MAX_DAYS(329)인 경우 period_type을 반환하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report="2023-09-30",
            reporting_periods=[
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 350,              # > 329이므로 세 조건 모두 탈락
                    "period_type": "Semi-Annual"  # fallback으로 반환될 값
                },
                {
                    "type": "duration",
                    "end_date": "2022-09-30", # 필터링에서 제외됨
                    "days": 90,
                    "period_type": "Quarterly"
                }
            ]
        )

    
        result = _determine_period_kind(stub_filing)
    
        assert result == "Semi-Annual"

    def test_determine_period_kind_raise_TypeError_when_days_is_None_among_multiple_periods(self, create_stub_filing):
        """days가 None인 경우 min() 비교에서 TypeError가 발생하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": None
                },
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 92
                }
            ]
        )

        with pytest.raises(TypeError):
            _determine_period_kind(stub_filing)

    def test_determine_period_kind_raise_ValueError_when_no_duration_type(self, create_stub_filing):
        """type이 duration인 period가 하나도 없는 경우 ValueError가 발생하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "instant",
                    "end_date": "2023-09-30",
                    "days": 92
                }
            ]
        )

        with pytest.raises(ValueError):
            _determine_period_kind(stub_filing)


    def test_determine_period_kind_return_QTD_at_boundary_100(self, create_stub_filing):
        """days=120일 때 QTD를 반환하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 120
                },
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 273
                }
            ]
        )

        result = _determine_period_kind(stub_filing)

        assert result == "QTD"

    
    def test_determine_period_kind_raise_ValueError_when_only_period_has_no_days(self, create_stub_filing):
        """period_at_end에 항목이 하나뿐이고 그 days가 None인 경우 ValueError가 발생"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": None
                }
            ]
        )

        with pytest.raises(ValueError):
            _determine_period_kind(stub_filing)

    def test_determine_period_kind_return_unknown_when_no_period_type(slef, create_stub_filing):
        """days > 329이고 period_type의 키가 없는 경우 'unknown'을 반환"""
        stub_filing = create_stub_filing(
            period_of_report="2023-09-30",
            reporting_periods=[
                {"type": "duration", "end_date": "2023-09-30", "days": 350}
                # no period_type dict
            ]
        )

        result = _determine_period_kind(stub_filing)

        assert result == "unknown"

class TestExtractRevenueByPeriodKind:
    @patch("app.modules.financial_extractor.revenue._determine_period_kind",return_value = "QTD")
    def test_extract_revenue_by_period_kind_return_edgartools_get_revenue_when_determine_period_kind_return_QTD(self, mock_determine, create_stub_filing):
        """기간 기준이 QTD이면 edgartools get_revenue()를 return한다."""
        #given
        expected_revenue = 100000
        stub_filing = create_stub_filing(
        period_of_report="2023-09-30",
        reporting_periods=[
            {"type": "duration", "end_date": "2023-09-30", "days": 92},
            {"type": "duration", "end_date": "2022-09-30", "days": 92},
            ]
        )
        #filing.obj().financials.get_revenue()
        stub_filing.obj.return_value.financials.get_revenue.return_value = expected_revenue

        # when
        result = get_revenue_qtd(stub_filing)

        #then
        stub_filing.obj.return_value.financials.get_revenue.assert_called_once()
        assert result == expected_revenue

    @patch("app.modules.financial_extractor.revenue._determine_period_kind",return_value = "YTD6")
    def test_get_revenue_qtd_return__convert_ytd9_to_quarterly_revenue_when_determine_period_kind_return_YTD6(self, mock_determine, create_stub_filing):
        """기간 기준이 QTD이면 edgartools get_revenue()를 return한다."""
        #given
        expected_revenue = 100000
        stub_filing = create_stub_filing(
        period_of_report="2023-09-30",
        reporting_periods=[
            {"type": "duration", "end_date": "2023-09-30", "days": 92},
            {"type": "duration", "end_date": "2022-09-30", "days": 92},
            ]
        )
        #filing.obj().financials.get_revenue()
        stub_filing.obj.return_value.financials.get_revenue.return_value = expected_revenue

        # when
        result = get_revenue_qtd(stub_filing)

        #then
        stub_filing.obj.return_value.financials.get_revenue.assert_called_once()
        assert result == expected_revenue



        

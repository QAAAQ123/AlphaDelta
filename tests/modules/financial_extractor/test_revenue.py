"""
매출 QTD 계산 모듈 테스트

_determine_period_kind(filing:Filing): QTD인지 YTD인지 확인하는 함수
정상1. days <= 130 => QTD return
정상2. days > 130이고 fiscal_period가 YTD6,YTD9 => YTD return
정상3. 1,2의 경우에 모두 맞지 않는 경우 =>  period_type return
예외1. days가 None인 경우 => TypeError 발생
예외2. type = "duration"이 없는 경우 => ValueError 발생
"""
from app.modules.financial_extractor.revenue import _determine_period_kind
from edgar import Filing
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

    def test_determine_period_kind_return_YTD(self, create_stub_filing):
        """_determine_period_kind가 YTD를 정상 return하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 182,
                    "fiscal_period": "YTD6"
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

        assert result == "YTD"

    def test_determine_period_kind_return_period_type(self, create_stub_filing):
            """_determine_period_kind가 QTD,YTD가 아니여서 period_type을 정상 return하는 경우"""
            stub_filing = create_stub_filing(
                period_of_report = "2023-09-30",
                reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 180,                   # 130 초과 (QTD 탈락) & min() 비교를 위한 유효 숫자
                    "fiscal_period": "OTHER",      # YTD6, YTD9 탈락
                    "period_type": "Semi-Annual"   # 최종 fallback으로 반환될 값
                },
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 273,
                    "fiscal_period": "YTD9",
                    "period_type": "Nine Months"
                },
                {
                    "type": "duration",
                    "end_date": "2022-09-30",
                    "days": 90,
                    "fiscal_period": "Q3",
                    "period_type": "Quarterly"
                }
                ]
            )
    
            result = _determine_period_kind(stub_filing)
    
            assert result == "Semi-Annual"

    def test_determine_period_kind_raise_TypeError_when_days_is_None(self, create_stub_filing):
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
        """days=100(경계값 포함)일 때 QTD를 반환하는 경우"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 100
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

    def test_determine_period_kind_return_YTD_when_days_just_above_100(self, create_stub_filing):
        """days=101(구 기준 130에서는 QTD였으나 신 기준 100에서는 YTD로 바뀌는 회귀 구간)"""
        stub_filing = create_stub_filing(
            period_of_report = "2023-09-30",
            reporting_periods = [
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 101,
                    "fiscal_period": "YTD6"
                },
                {
                    "type": "duration",
                    "end_date": "2023-09-30",
                    "days": 273
                }
            ]
        )

        result = _determine_period_kind(stub_filing)

        assert result == "YTD"


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
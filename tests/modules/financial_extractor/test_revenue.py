"""
매출 QTD 계산 모듈 테스트

_determine_period_kind(filing:Filing): QTD인지 YTD인지 확인하는 함수
정상1. days <= 130이면 QTD
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

        assert result is "QTD"
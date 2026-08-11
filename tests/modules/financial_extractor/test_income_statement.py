"""
손익계산서 항목 QTD 추출 모듈 단위 테스트
1. _get_revenue_qtd_from_10_q 
"""
from app.modules.financial_extractor.income_statement import _get_revenue_qtd_from_10_q
import pytest_mock
"""
_get_revenue_qtd_from_10_q(financials: Any) -> int | float | None
예외1. financials가 없을 때 -> None return
예외2. get_revenue()의 값이 없을 때 -> None return
정상1. get_revenue()의 값이 정상일 때 -> revnue(int or float) return
"""

class TestGetRevenueQtdFrom10Q:
    def test_get_revenue_qtd_from_10_q_return_none_when_financials_is_none(self):
        #예외1. financials가 없을 때 -> None return
        mock_financials = None

        result = _get_revenue_qtd_from_10_q(mock_financials)

        assert result is None

    def test_get_revenue_qtd_from_10_q_return_none_when_get_revenue_has_no_value(self,mocker):
        #예외2. get_revenue()의 값이 없을 때 -> None return
        mock_financials = mocker.MagicMock()
        mock_financials.get_revenue.return_value = None

        result = _get_revenue_qtd_from_10_q(mock_financials)

        assert result is None
        assert mock_financials.get_revenue.call_count == 1

    def test_get_revenue_qtd_from_10_q_return_int_revnue_when_valid(self, mocker):
        #정상1. get_revenue()의 값이 정상일 때 -> revnue(int) return
        mock_financials = mocker.MagicMock()
        mock_financials.get_revenue.return_value = 10000

        result = _get_revenue_qtd_from_10_q(mock_financials)

        assert result == 10000
        assert mock_financials.get_revenue.call_count == 1

    def test_get_revenue_qtd_from_10_q_return_float_revnue_when_valid(self, mocker):
            #정상1. get_revenue()의 값이 정상일 때 -> revnue(float) return
            mock_financials = mocker.MagicMock()
            mock_financials.get_revenue.return_value = 10000.5
    
            result = _get_revenue_qtd_from_10_q(mock_financials)
    
            assert result == 10000.5
            assert mock_financials.get_revenue.call_count == 1
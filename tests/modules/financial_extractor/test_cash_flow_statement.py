import pytest
from app.modules.financial_extractor.cash_flow_statement import (
    _convert_to_qtd
)
from app.models.enum import *
from edgar import Financials

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
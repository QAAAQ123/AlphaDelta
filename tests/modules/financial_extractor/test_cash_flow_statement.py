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
"""
def _extract_month(date_str: str | None, value_name: str) -> int | None:
mocking: 없음

1. date_str 없음 -> None return
2. value_name이 fiscal_year_end,period_of_report 중 하나가 아님 -> None return
3. date_str을 integer로 변환 불가 -> None return
4. month가 1-12사이의 값이 아님 -> None return
5. date_str이 start 값보다 작은 경우 -> None return(ValueError)
정상 6. fiscal_year_end와 정상 date_str -> month return
정상 7. period_of_report과 정상 date_str -> month return
"""
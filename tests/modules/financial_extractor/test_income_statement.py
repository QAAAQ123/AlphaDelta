#손익계산서 항목 QTD 추출 모듈 단위 테스트
#1. _get_revenue_from_edgartools
#2. get_revenue_qtd
#3. _get_revenue_qtd_from_10_k
from app.modules.financial_extractor.income_statement import _get_revenue_from_edgartools,get_revenue_qtd,_get_revenue_qtd_from_10_k
import pytest_mock
import pytest
from edgar import Filing

@pytest.fixture
def filing_factory(mocker):
    def _create_filing(
        revenue=None, form=None, has_financials=True, raise_error=None
    ):
        # 1. filing 객체 생성
        # spec을 지정하거나 PropertyMock/delattr을 사용하여 filing.financials 접근을 강제로 금지합니다.
        mock_filing = mocker.MagicMock()

        # filing.form 설정
        mock_filing.form = form

        # 2. filing.obj() 단계 구성
        if has_financials:
            mock_financials = mocker.MagicMock()

            # 예외 및 정상 반환값 설정
            if raise_error == "AttributeError":
                mock_financials.get_revenue.side_effect = AttributeError(
                    "AttributeError 발생"
                )
            elif raise_error == "Exception":
                mock_financials.get_revenue.side_effect = Exception(
                    "Exception 발생"
                )
            else:
                mock_financials.get_revenue.return_value = revenue

            # filing.obj().financials 연결
            mock_filing.obj.return_value.financials = mock_financials
        else:
            # financials가 없는 경우
            mock_filing.obj.return_value.financials = None

        return mock_filing

    return _create_filing

"""
_get_revenue_from_edgartools(financials: Any) -> int | float | None
예외1. financials가 없을 때 -> None return
예외2. get_revenue()의 값이 없을 때 -> None return
정상1. get_revenue()의 값이 정상일 때 -> revnue(int or float) return
"""
class TestGetRevenueFromEdgartools:
    def test_get_revenue_from_edgartools_return_none_when_financials_is_none(self):
        #예외1. financials가 없을 때 -> None return
        mock_financials = None

        result = _get_revenue_from_edgartools(mock_financials)

        assert result is None

    def test_get_revenue_from_edgartools_return_none_when_get_revenue_has_no_value(self,mocker):
        #예외2. get_revenue()의 값이 없을 때 -> None return
        mock_financials = mocker.MagicMock()
        mock_financials.get_revenue.return_value = None

        result = _get_revenue_from_edgartools(mock_financials)

        assert result is None
        assert mock_financials.get_revenue.call_count == 1

    def test_get_revenue_from_edgartools_return_int_revnue_when_valid(self, mocker):
        #정상1. get_revenue()의 값이 정상일 때 -> revnue(int) return
        mock_financials = mocker.MagicMock()
        mock_financials.get_revenue.return_value = 10000

        result = _get_revenue_from_edgartools(mock_financials)

        assert result == 10000
        assert mock_financials.get_revenue.call_count == 1

    def test_get_revenue_from_edgartools_return_float_revnue_when_valid(self, mocker):
            #정상1. get_revenue()의 값이 정상일 때 -> revnue(float) return
            mock_financials = mocker.MagicMock()
            mock_financials.get_revenue.return_value = 10000.5
    
            result = _get_revenue_from_edgartools(mock_financials)
    
            assert result == 10000.5
            assert mock_financials.get_revenue.call_count == 1


"""
get_revenue_qtd(filing: Filing) -> int | float | None:
예외1. filing이 없을 때 -> None return
정상1. filing.form이 10-Q,10-Q/A일 때 -> revenue return
정상2. filng.form이 10-K,10-K/A일 때 -> revneue return
"""
class TestGetRevenueQtd:
    def test_get_revenue_qtd_return_none_when_filing_is_none(self):
        #예외1. filing이 없을 때 -> None return
        filing = None

        result = get_revenue_qtd(filing)

        assert result is None

    def test_get_revenue_qtd_return_revenue_when_filing_form_is_10_q(self, mocker, filing_factory):
        #정상1. filing.form이 10-Q,10-Q/A일 때 -> revenue return
        mock_filing = filing_factory(form="10-Q/A",revenue=100000)
        mock_get_revenue_qtd_from_10_q = mocker.patch(
            "app.modules.financial_extractor.income_statement._get_revenue_qtd_from_10_q",
            return_value = 100000
        )

        result = get_revenue_qtd(mock_filing)

        assert result == 100000
        mock_get_revenue_qtd_from_10_q.assert_called_once_with(mock_filing.obj().financials)

    def test_get_revenue_qtd_return_revenue_when_fiilng_form_is_10_k(self, mocker, filing_factory):
        # 정상2. filng.form이 10-K,10-K/A일 때 -> revneue return
        mock_filing = filing_factory(form="10-K/A",revenue=10000000)
        mock_get_revenue_qtd_from_10_k = mocker.patch(
                    "app.modules.financial_extractor.income_statement._get_revenue_qtd_from_10_k",
                    return_value = 10000000
                )
        
        result = get_revenue_qtd(mock_filing)
        
        assert result == 10000000
        mock_get_revenue_qtd_from_10_k.assert_called_once_with(mock_filing)

"""
3. _get_revenue_qtd_from_10_k
예외1. _get_revenue_from_edgartools helper에서 None을 return 할 때 -> None return
예외2. _get_revenue_from_edgartools
"""
class TestGetRevenueQtdFrom10K:
    def test_get_revenue_qtd_from_10_k_return_none_when_helper_return_none(self,mocker, filing_factory):
        mock_filing = filing_factory(has_financials=False)
        mock_helper = mocker.patch(
            "app.modules.financial_extractor.income_statement._get_revenue_from_edgartools",
            return_value=None
        )


        result = _get_revenue_qtd_from_10_k(mock_filing)

        assert result is None
        mock_helper.assert_called_once_with(mock_filing.obj().financials)
        

"""
# 매출 QTD 계산 모듈 단위 테스트

1. get_revenue_qtd(filing)
정상1. 10-K가 아닌 10-Q 공시가 들어왔을 때 -> revenue return
정상2. 10-K 공시가 들어왔을 때 -> QTD revenue return



3. _extract_primary_period_meta
"""
import pytest
from edgar import Filing
from app.modules.financial_extractor.revenue import _get_income_statement


"""
1. _get_income_statement(filing):
책임1-손익 계산서를 Filing 객체에서 추출
예외1. obj().financials가 None -> None return
정상1. obj().financials.income_statement가 존재 -> income_statement return
"""
class TestGetIncomeStatment:
    def test_get_income_statement_return_none_when_financials_is_none(self, mocker):
        """예외1. obj().financials가 None -> None return"""
        stub_filing = mocker.MagicMock(spec=Filing)
        stub_filing.obj.return_value.financials = None

        result = _get_income_statement(stub_filing)

        assert result == None

    def test_get_income_statement_return_dataframe_when_financials_is_not_none(self, mocker):
        """정상1. obj().financials가 존재 -> pd.DataFrame(손익계산서) return"""
        #given
        stub_filing = mocker.MagicMock(spec=Filing)
        stub_df = mocker.MagicMock()
        mock_financials = stub_filing.obj.return_value.financials
        mock_financials.income_statement.return_value.render.return_value.to_dataframe.return_value = stub_df

        #when
        result = _get_income_statement(stub_filing)

        #then
        assert result == stub_df
        mock_financials.income_statement.assert_called_once()





class TestGetRevenueQTD:
    def test_get_revenue_qtd_return_reveue_qtd_when_filing_is_not_10_k():
        pass




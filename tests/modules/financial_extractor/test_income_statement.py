#손익계산서 항목 QTD 추출 모듈 단위 테스트
#1. _get_revenue_from_edgartools
#2. get_revenue_qtd
#3. _get_revenue_qtd_from_10_k
from app.modules.financial_extractor.income_statement import (
    get_revenue_qtd,
    _get_revenue_from_edgartools,
    _get_revenue_qtd_from_10_k,
    _get_prior_three_10_q_filings,
    _deduplicate_by_period,
    _get_last_3_periods,
    _calc_10_k_revenue_qtd,
    _extract_revenues_from_filings
)
import pytest
from datetime import date
from edgar import Company,Filing

@pytest.fixture
def filing_factory(mocker):
    def _create_filing(
        fiscal_year_end=None,revenue=None, form=None, has_financials=True, raise_error=None,period_of_report=None
    ):
        # 1. filing 객체 생성
        # spec을 지정하거나 PropertyMock/delattr을 사용하여 filing.financials 접근을 강제로 금지합니다.
        mock_filing = mocker.MagicMock(spec=Filing)

        # filing.form 설정
        mock_filing.form = form

        # filing.period_of_report 설정
        mock_filing.period_of_report = period_of_report

        mock_filing.fiscal_year_end = fiscal_year_end

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


@pytest.fixture
def company_factory(mocker,filing_factory):
    def _create_company(mock_filing_list=None, raise_error=None):
        mock_company = mocker.MagicMock(spec=Company)
        if raise_error:
            mock_company.get_filings.side_effect = raise_error
        else: 
            mock_company.get_filings.return_value.filter.return_value.latest.return_value = mock_filing_list
        return mock_company

    return _create_company

"""
1. _get_revenue_from_edgartools(financials: Any) -> int | float | None
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
2. get_revenue_qtd(filing: Filing) -> int | float | None:
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
            "app.modules.financial_extractor.income_statement._get_revenue_from_edgartools",
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

"""
4. _get_prior_three_10_q_filings
예외1. get_filings().filter().latest() 호출 중 에러 발생 -> RuntimeError
예외2. _get_last_3_periods가 None을 반환할 때 -> None return
정상1. _get_last_3_periods가 list[Filing]을 반환할 때 -> 그 list 그대로 return
"""
class TestGetPriorThree10QFilings:
    def test_raise_runtime_error_when_extrnal_api_fails(self, company_factory):
        #예외1. get_filings().filter().latest() 호출 중 에러 발생 -> RuntimeError
        mock_company = company_factory(raise_error=Exception("API Error"))

        with pytest.raises(RuntimeError, match="Edgartools 요청 중 알 수 없는 문제 발생: "):
            _get_prior_three_10_q_filings(mock_company, "2024-02-20")

    def test_return_none_when_helpers_return_none(self, mocker, company_factory, filing_factory):
        #예외2. _get_last_3_periods가 None을 반환할 때 -> None return
        mock_filings = [filing_factory(period_of_report="2022-03-31", form="10-Q")]
        mock_company = company_factory(mock_filings)

        mocker.patch(f"app.modules.financial_extractor.income_statement._get_last_3_periods", return_value = None)

        result = _get_prior_three_10_q_filings(mock_company,"2024-02-20")

        assert result is None

    def test_return_filing_list_when_helpers_succed(self,mocker, company_factory, filing_factory):
        #정상1. _get_last_3_periods가 list[Filing]을 반환할 때 -> 그 list 그대로 return
        mock_filings = [
            filing_factory(period_of_report="2022-03-31", form="10-Q"),
            filing_factory(period_of_report="2022-06-30", form="10-Q"),
            filing_factory(period_of_report="2022-09-30", form="10-Q"),
        ]
        mock_company = company_factory(mock_filings)
        expected_result = mock_filings[-3:]

        mocker.patch(f"app.modules.financial_extractor.income_statement._get_last_3_periods", return_value=expected_result)

        result = _get_prior_three_10_q_filings(mock_company, "2024-02-20")

        assert result == expected_result

"""
5. _deduplicate_by_period
예외1. 인자 candidate_filings의 len이 0일 때 -> empty dict return
정상1. 모두 10-Q만 있을 때 -> 개수 동일
정상2. 같은 period에 10-Q/A가 있으면 -> /A가 선택돼야 함
정상2-1. 10-Q와 10-Q/A가 섞여 있으면 -> key의 개수가 candidate_filings보다 작아야함
"""
class TestDeduplicateByPeriod:
    def test_return_empty_dict_when_arg_is_empty_list(self):
        #예외1. 인자 candidate_filings의 len이 0일 때 -> empty dict return
        stub_candidate_filings = []

        result = _deduplicate_by_period(stub_candidate_filings)

        assert result == {}

    @pytest.mark.parametrize(
        "mock_candidate_filings_param",
       [
            [
                ("2022-06-30", "10-Q"),
                ("2022-03-30", "10-Q"),
                ("2022-09-30", "10-Q"),
            ],
            [
                ("2021-12-31", "10-Q"),
                ("2022-06-30", "10-Q"),
                ("2022-03-30", "10-Q"),
                ("2022-09-30", "10-Q"),
            ],
        ]
    )
    def test_returns_dict_with_same_key_count_when_no_amendments(self,filing_factory,mock_candidate_filings_param):
        #정상1. 모두 10-Q만 있을 때 -> 개수 동일
        mock_candidate_filings = [
            filing_factory(period_of_report = period, form = form)
            for period, form in mock_candidate_filings_param
        ]

        result = _deduplicate_by_period(mock_candidate_filings)

        assert len(result) == len(mock_candidate_filings)
        expected_periods = {f.period_of_report for f in mock_candidate_filings}
        assert set(result.keys()) == expected_periods

    def test_amendment_filing_is_selected(self, filing_factory):
        original = filing_factory(period_of_report = "2022-06-31", form="10-Q")
        amendment = filing_factory(period_of_report = "2022-06-31", form="10-Q/A")

        result = _deduplicate_by_period([original,amendment])

        assert result["2022-06-31"] is amendment
        assert result["2022-06-31"] is not original
        
    @pytest.mark.parametrize(
            "mock_candidate_filings_param",
           [
                [
                    ("2022-06-30", "10-Q"),
                    ("2022-03-30", "10-Q"),
                    ("2022-03-30", "10-Q/A"),
                    ("2022-09-30", "10-Q"),
                ],
                [
                    ("2021-12-31", "10-Q"),
                    ("2021-12-31", "10-Q/A"),
                    ("2022-06-30", "10-Q"),
                    ("2022-06-30", "10-Q/A"),
                    ("2022-03-30", "10-Q"),
                    ("2022-09-30", "10-Q"),
                ],
            ]
        )
    def test_return_dict_with_diff_key_conut_when_has_amendments(self, filing_factory, mock_candidate_filings_param):
        #정상2-1. 10-Q와 10-Q/A가 섞여 있으면 -> key의 개수가 candidate_filings보다 작아야함
        mock_candidate_filings = [
            filing_factory(period_of_report = period, form = form)
            for period, form in mock_candidate_filings_param
        ]

        result = _deduplicate_by_period(mock_candidate_filings)

        assert len(result) != len(mock_candidate_filings)
        expected_periods = {f.period_of_report for f in mock_candidate_filings}
        assert set(result.keys()) == expected_periods

"""
6. _get_last_3_periods
예외1. by_period의 개수가 2개 이하일 때 -> None return
정상1. by_period가 3개 이상일 때 -> list[Filing] return
"""
class TestGetLast3Periods:
    @pytest.mark.parametrize(
            "mock_by_period",
            [
                {}, #0개일 때
                {"2022-06-30": "body1"},  # 1개일 때
                {"2022-06-30": "body1", "2022-03-31": "body2"},  # 2개일 때
            ]
    )
    def test_returns_none_when_by_period_count_is_2_or_less(self,mock_by_period):
        #예외1. by_period의 개수가 2개 이하일 때 -> None return
        result = _get_last_3_periods(mock_by_period)

        assert result is None

    @pytest.mark.parametrize(
            "mock_by_period",
            [
                {"2022-06-30": "body1", "2022-03-31": "body2", "2022-09-31": "body3"}, #3개일 때
                {"2022-06-30": "body1", "2022-03-31": "body2", "2022-09-31": "body3", "2021-09-31": "body4"}  # 4개일 때
                
            ]
    )
    def test_returns_filing_list_when_by_period_count_is_3_or_more(self, mock_by_period):
        #정상1. by_period가 3개 이상일 때 -> list[Filing] return
        result = _get_last_3_periods(mock_by_period)

        assert len(result) == 3
        sorted_periods = sorted(mock_by_period.keys())
        expected = [mock_by_period[p] for p in sorted_periods[-3:]]
        assert result == expected


"""
7. _calc_10_k_revenue_qtd
예외1. q1_q2_q3_revenues의 길이가 3이 아닌 경우 -> None return
예외2. q1_q2_q3_revenues의 값중 하나라도 None인 경우 -> None return
정상1. 모든 값이 정상일 때 -> Q4 QTD return
"""
class TestCalc10KRevenueQtd:
    def test_returns_none_when_revenue_count_is_not_3(self):
        #예외1. q1_q2_q3_revenues의 길이가 3이 아닌 경우 -> None return
        result = _calc_10_k_revenue_qtd(1000, [200, 250])
        assert result is None

    def test_returns_none_when_any_revenue_is_none(self):
        #예외2. q1_q2_q3_revenues의 값중 하나라도 None인 경우 -> None return
        result = _calc_10_k_revenue_qtd(1000, [200, None, 300])
        assert result is None

    def test_returns_qtd_revenue_when_all_value_present(self):
        #정상1. 모든 값이 정상일 때 -> Q4 QTD return
        result = _calc_10_k_revenue_qtd(1000,[200,250,300])
        assert result == 250

"""
8. _extract_revenues_from_filings
정상1. 여러 filing을 순회하며 각각 revenue를 추출하는지
예외1. 일부 filing에서 revenue가 None이어도 전체가 죽지 않고 리스트에 None으로 담기는지
예외2. 빈 리스트가 들어오면 빈 리스트가 나오는지 
"""
class TestExtractRevenuesFromFilings:
    def test_includes_none_when_some_filing_has_no_revenue(self, filing_factory):
        filings = [
            filing_factory(revenue=100),
            filing_factory(has_financials=False), 
            filing_factory(revenue=300),
        ]

        result = _extract_revenues_from_filings(filings)

        assert result == [100, None, 300]

    def test_returns_empty_list_when_filings_is_empty(self):
        result = _extract_revenues_from_filings([])

        assert result == []

    
    def test_extracts_revenue_from_each_filing_in_order(self, mocker, filing_factory):
        filings = [
            filing_factory(revenue=100),
            filing_factory(revenue=200),
            filing_factory(revenue=300),
        ]

        result = _extract_revenues_from_filings(filings)

        assert result == [100, 200, 300]
"""
단위 테스트 코드
1. _is_amendment_form
    예외1. raw_form이 str 타입이 아닌 인자가 들어올 때 -> AttributeError 발생
    정상1. 10-K,10-Q \A로 끝나지 않는 인자가 들어올 때 -> False return
    정상2. 10-K/A,10-Q/A \A로 끝나는 인자가 들어올 때 -> True return
2. _map_form_type
    예외1. raw_form이 str 타입이 아닌 인자가 들어올 때 -> AttributeError 발생
    정상1. 10-K가 들어올 때 -> FormType.REGULAR_10_K return
    정상2. 10-K/A가 들어올 때 -> FormType.AMENDMENT_10_K_A return
    정상3. 10-Q가 들어올 때 -> FormType.REGULAR_10_Q return
    정상4. 10-Q/A가 들어올 때 -> FormType.AMENDMENT_10_Q_A return
3. _get_parent_form_type
    예외1. child_form_tpye이 FormType이 아닐 때 -> ValueError 발생
    정상1. FormType.AMENDMENT_10_K_A이 들어올 때 -> FormType.REGULAR_10_K return
    정상2. FormType.AMENDMENT_10_Q_A이 들어올 때 -> FormType.REGULAR_10_Q return
    정상3. FormType.REGULAR_10_Q or REGULAR_10_K가 들어올 때 -> 인자를 그대로 return
4. _parse_year_and_quarter
    예외1. period_of_report이 YYYY-mm-dd 형식이 아닐 때 -> ValueError 발생
    예외2. period_of_report이 str type이 아닐 때 -> AttributeError 발생
    예외3. period_of_report이 존재할 수 없는 날짜일 때 -> ValueError 발생
    정상 상황: period_of_report의 mm이 1-12 중 하나이고 존재하는 연도와 일일 때 -> (report_date.year, Quarter) tuple return
5. classify_and_build_original_filings
    filing_data가 None인 경우는 service에서 거르기 때문에 검사 불필요
    예외1. filing_data가 None인 경우 -> TypeError 발생 (NoneType은 반복 가능한 객체가 아님)
    예외2. company_id가 None이거나 int가 아닌 경우 -> pydantic.ValidationError 발생 (`FilingCreate` 생성 시 타입 검증 실패)
    정상1. filing_data:정상 공시20개/existing_accessions:None -> len(original_filings): 20개, amendment_filings: 0개
    정상2. filing_data:정상 공시20개,수정공시 2개/existing_accessions:None -> len(original_filings): 20개, amendment_filings: 2개
    정상3. filing_data:정상 공시 10개/existing_accessions:10개(모두 겹침) -> len(original_filings): 0개, amendment_filings: 0개
    정상4. filing_data:정상 공시 10개/existing_accessions:10개(모두 안겹침) -> len(original_filings): 10개, amendment_filings: 0개
6. build_amendment_filings
    예외1. company_id만 None | int아님 -> pydantic.ValidationError 발생 (`FilingCreate` 생성 시 company_id 타입 검증 실패)
    예외2. parent_map이 None -> AttributeError 발생 (NoneType에 대해 `.get` 호출 시)
    정상1. amendment_filings이 None -> 빈 list return
    정상2. amendment_filings이 3개 -> 길이 3의 amendment_schemas return
7. build_parent_map
    예외1. flings이 None -> TypeError 발생 (NoneType은 반복 가능한 객체가 아님)
    정상1. filing이 정상 -> (form_tye,year,quarter): id 튜플의 dict
""" 

import pytest
from datetime import date
from types import SimpleNamespace
from pydantic import ValidationError

from app.models.base import FormType, Quarter
from app.modules.past_filings import builder


def make_filing(accession_number: str, period_of_report: str, form: str):
    return SimpleNamespace(
        accession_number=accession_number,
        period_of_report=period_of_report,
        form=form,
        document=SimpleNamespace(document_type="primary_doc.html"),
        filing_date=date(2024, 1, 1),
    )


class TestIsAmendmentForm:
    def test_non_string_raw_form_raises_attribute_error(self):
        """예외1. raw_form이 str 타입이 아닌 인자가 들어올 때 -> AttributeError 발생"""
        with pytest.raises(AttributeError):
            builder._is_amendment_form(None)

    def test_regular_forms_return_false(self):
        """정상1. 10-K,10-Q \A로 끝나지 않는 인자가 들어올 때 -> False return"""
        assert builder._is_amendment_form("10-K") is False
        assert builder._is_amendment_form("10-Q") is False

    def test_amendment_forms_return_true(self):
        """정상2. 10-K/A,10-Q/A \A로 끝나는 인자가 들어올 때 -> True return"""
        assert builder._is_amendment_form("10-K/A") is True
        assert builder._is_amendment_form("10-Q/A") is True


class TestMapFormType:
    def test_non_string_raw_form_raises_attribute_error(self):
        """예외1. raw_form이 str 타입이 아닌 인자가 들어올 때 -> AttributeError 발생"""
        with pytest.raises(AttributeError):
            builder._map_form_type(None)

    def test_10_k_maps_to_regular_10_k(self):
        """정상1. 10-K가 들어올 때 -> FormType.REGULAR_10_K return"""
        assert builder._map_form_type("10-K") == FormType.REGULAR_10_K

    def test_10_k_a_maps_to_amendment_10_k_a(self):
        """정상2. 10-K/A가 들어올 때 -> FormType.AMENDMENT_10_K_A return"""
        assert builder._map_form_type("10-K/A") == FormType.AMENDMENT_10_K_A

    def test_10_q_maps_to_regular_10_q(self):
        """정상3. 10-Q가 들어올 때 -> FormType.REGULAR_10_Q return"""
        assert builder._map_form_type("10-Q") == FormType.REGULAR_10_Q

    def test_10_q_a_maps_to_amendment_10_q_a(self):
        """정상4. 10-Q/A가 들어올 때 -> FormType.AMENDMENT_10_Q_A return"""
        assert builder._map_form_type("10-Q/A") == FormType.AMENDMENT_10_Q_A


class TestGetParentFormType:
    def test_amendment_10_k_a_returns_regular_10_k(self):
        """정상1. FormType.AMENDMENT_10_K_A이 들어올 때 -> FormType.REGULAR_10_K return"""
        assert builder._get_parent_form_type(FormType.AMENDMENT_10_K_A) == FormType.REGULAR_10_K

    def test_amendment_10_q_a_returns_regular_10_q(self):
        """정상2. FormType.AMENDMENT_10_Q_A이 들어올 때 -> FormType.REGULAR_10_Q return"""
        assert builder._get_parent_form_type(FormType.AMENDMENT_10_Q_A) == FormType.REGULAR_10_Q

    def test_regular_form_types_raise_value_error(self):
        """예외1. child_form_type이 FormType이 아닐 때 -> ValueError 발생"""
        with pytest.raises(ValueError):
            builder._get_parent_form_type(FormType.REGULAR_10_K)

        with pytest.raises(ValueError):
            builder._get_parent_form_type(FormType.REGULAR_10_Q)


class TestParseYearAndQuarter:
    def test_invalid_format_raises_value_error(self):
        """예외1. period_of_report이 YYYY-mm-dd 형식이 아닐 때 -> ValueError 발생"""
        with pytest.raises(ValueError):
            builder._parse_year_and_quarter("2024/03/31")

    def test_non_string_input_raises_type_error(self):
        """예외2. period_of_report이 str type이 아닐 때 -> TypeError 발생"""
        with pytest.raises(TypeError):
            builder._parse_year_and_quarter(None)

    def test_invalid_date_raises_value_error(self):
        """예외3. period_of_report이 존재할 수 없는 날짜일 때 -> ValueError 발생"""
        with pytest.raises(ValueError):
            builder._parse_year_and_quarter("2024-02-30")

    def test_valid_date_returns_year_and_quarter(self):
        """정상. period_of_report의 mm이 1-12 중 하나이고 존재하는 연도와 일일 때 -> (report_date.year, Quarter) tuple return"""
        year, quarter = builder._parse_year_and_quarter("2024-03-31")
        assert year == 2024
        assert quarter == Quarter.Q1


class TestClassifyAndBuildOriginalFilings:
    def test_filing_data_none_raises_type_error(self):
        """예외1. filing_data가 None인 경우 -> TypeError 발생 (NoneType은 반복 가능한 객체가 아님)"""
        with pytest.raises(TypeError):
            builder.classify_and_build_original_filings(None, 1, set())

    def test_company_id_invalid_raises_validation_error(self):
        """예외2. company_id가 None이거나 int가 아닌 경우 -> pydantic.ValidationError 발생"""
        filings = [make_filing("0001", "2024-03-31", "10-K")]
        with pytest.raises(ValidationError):
            builder.classify_and_build_original_filings(filings, None, set())

    def test_existing_accessions_none_raises_type_error(self):
        """existing_accessions이 None일 때 -> TypeError 발생"""
        filings = [make_filing(str(i), "2024-03-31", "10-K") for i in range(20)]

        with pytest.raises(TypeError):
            builder.classify_and_build_original_filings(filings, 1, None)

    def test_all_existing_accessions_are_skipped(self):
        """정상3. filing_data:정상 공시 10개/existing_accessions:10개(모두 겹침) -> len(original_filings): 0개, amendment_filings: 0개"""
        filings = [make_filing(str(i), "2024-03-31", "10-K") for i in range(10)]
        existing_accessions = {str(i) for i in range(10)}

        original_filings, amendment_filings = builder.classify_and_build_original_filings(
            filings, 1, existing_accessions
        )

        assert len(original_filings) == 0
        assert len(amendment_filings) == 0

    def test_no_existing_accessions_returns_all_original_filings(self):
        """정상4. filing_data:정상 공시 10개/existing_accessions:10개(모두 안겹침) -> len(original_filings): 10개, amendment_filings: 0개"""
        filings = [make_filing(str(i), "2024-03-31", "10-K") for i in range(10)]

        original_filings, amendment_filings = builder.classify_and_build_original_filings(
            filings, 1, set()
        )

        assert len(original_filings) == 10
        assert len(amendment_filings) == 0

    def test_amendment_filings_are_separated_from_originals(self):
        """정상2. filing_data:정상 공시20개,수정공시 2개/existing_accessions:None -> len(original_filings): 20개, amendment_filings: 2개"""
        filings = [
            make_filing(str(i), "2024-03-31", "10-K") for i in range(20)
        ] + [make_filing("A001", "2024-03-31", "10-K/A") for _ in range(2)]

        original_filings, amendment_filings = builder.classify_and_build_original_filings(
            filings, 1, set()
        )

        assert len(original_filings) == 20
        assert len(amendment_filings) == 2


class TestBuildAmendmentFilings:
    def test_amendment_filings_none_raises_type_error(self):
        """amendment_filings이 None일 때 -> TypeError 발생"""
        with pytest.raises(TypeError):
            builder.build_amendment_filings(None, 1, {})

    def test_invalid_company_id_raises_validation_error(self):
        """예외1. company_id만 None | int아님 -> pydantic.ValidationError 발생"""
        amendment_filings = [make_filing("A001", "2024-03-31", "10-K/A")]
        with pytest.raises(ValidationError):
            builder.build_amendment_filings(amendment_filings, None, {})

    def test_parent_map_none_raises_attribute_error(self):
        """예외2. parent_map이 None -> AttributeError 발생 (NoneType에 대해 `.get` 호출 시)"""
        amendment_filings = [make_filing("A001", "2024-03-31", "10-K/A")]
        with pytest.raises(AttributeError):
            builder.build_amendment_filings(amendment_filings, 1, None)

    def test_builds_three_amendment_schemas(self):
        """정상2. amendment_filings이 3개 -> 길이 3의 amendment_schemas return"""
        amendment_filings = [
            make_filing(f"A00{i}", "2024-03-31", "10-Q/A") for i in range(3)
        ]
        schemas = builder.build_amendment_filings(
            amendment_filings,
            1,
            {(FormType.REGULAR_10_Q, 2024, Quarter.Q1): 100},
        )

        assert len(schemas) == 3
        assert all(schema.company_id == 1 for schema in schemas)
        assert all(schema.form_type == FormType.AMENDMENT_10_Q_A for schema in schemas)


class TestBuildParentMap:
    def test_filing_list_none_raises_type_error(self):
        """예외1. filings이 None -> TypeError 발생 (NoneType은 반복 가능한 객체가 아님)"""
        with pytest.raises(TypeError):
            builder.build_parent_map(None)

    def test_builds_parent_map_from_filings(self):
        """정상1. filing이 정상 -> (form_type,year,quarter): id 튜플의 dict"""
        filings = [
            SimpleNamespace(form_type=FormType.REGULAR_10_Q, year=2024, quarter=Quarter.Q1, id=1),
            SimpleNamespace(form_type=FormType.REGULAR_10_K, year=2024, quarter=Quarter.Q1, id=2),
        ]

        result = builder.build_parent_map(filings)

        assert result == {
            (FormType.REGULAR_10_Q, 2024, Quarter.Q1): 1,
            (FormType.REGULAR_10_K, 2024, Quarter.Q1): 2,
        }

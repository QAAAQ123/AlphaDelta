"""
단위 테스트 코드
1. fetch_past_20_quarters_filings_info
    정상1. get_filings에서 정상 데이터가 반환될 때 -> not_amended_filings 20개 + amended_filings 필터 후 합산 반환
    정상2. amended_filings에 period_of_report가 not_amended_filings 대상 기간과 일치하지 않는 경우 -> 최종 리스트에 포함되지 않음
    예외1. edgartools 호출 중 예외가 발생할 때 -> 빈 리스트 반환

2. _extract_periods
    정상1. filings 목록에 period_of_report가 모두 있을 때 -> 중복 제거된 set 반환

3. _filter_amendments_by_period
    정상1. amended_filings가 target_periods에 일치하는 항목만 반환
    정상2. amended_filings가 target_periods에 하나도 일치하지 않을 때 -> 빈 리스트 반환
"""
from types import SimpleNamespace

from app.modules.past_filings import fetcher


class FakeFilings(list):
    def head(self, count):
        return list(self)[:count]


class TestExtractPeriods:
    def test_extracts_unique_periods(self):
        """정상1. filings 목록에 period_of_report가 모두 있을 때 -> 중복 제거된 set 반환"""
        filings = [
            SimpleNamespace(period_of_report="2024-03-31"),
            SimpleNamespace(period_of_report="2024-03-31"),
            SimpleNamespace(period_of_report="2024-06-30"),
        ]

        result = fetcher._extract_periods(filings)

        assert result == {"2024-03-31", "2024-06-30"}


class TestFilterAmendmentsByPeriod:
    def test_filters_amendments_by_target_periods(self):
        """정상1. amended_filings가 target_periods에 일치하는 항목만 반환"""
        amended_filings = [
            SimpleNamespace(period_of_report="2024-03-31"),
            SimpleNamespace(period_of_report="2024-06-30"),
            SimpleNamespace(period_of_report="2024-09-30"),
        ]
        target_periods = {"2024-03-31", "2024-09-30"}

        result = fetcher._filter_amendments_by_period(amended_filings, target_periods)

        assert result == [amended_filings[0], amended_filings[2]]

    def test_returns_empty_list_when_no_match(self):
        """정상2. amended_filings가 target_periods에 하나도 일치하지 않을 때 -> 빈 리스트 반환"""
        amended_filings = [
            SimpleNamespace(period_of_report="2024-01-31"),
            SimpleNamespace(period_of_report="2024-02-28"),
        ]
        target_periods = {"2024-03-31"}

        result = fetcher._filter_amendments_by_period(amended_filings, target_periods)

        assert result == []


class TestFetchPast20QuartersFilingsInfo:
    def test_returns_combined_non_amended_and_matched_amended_filings(self, mocker):
        """정상1. get_filings에서 정상 데이터가 반환될 때 -> not_amended_filings 20개 + amended_filings 필터 후 합산 반환"""
        mock_company = mocker.Mock()
        not_amended_filings = FakeFilings(
            [SimpleNamespace(period_of_report="2024-03-31", accession_number=str(i)) for i in range(20)]
        )
        all_amended_filings = [
            SimpleNamespace(period_of_report="2024-03-31", accession_number="A001"),
            SimpleNamespace(period_of_report="2024-01-31", accession_number="A002"),
        ]

        def get_filings(form, amendments=None):
            if amendments is False:
                return not_amended_filings
            return all_amended_filings

        mock_company.get_filings.side_effect = get_filings
        mocker.patch("app.modules.past_filings.fetcher.Company", return_value=mock_company)

        result = fetcher.fetch_past_20_quarters_filings_info("0000000000")

        assert len(result) == 21
        assert any(item.accession_number == "A001" for item in result)
        assert all(
            hasattr(item, "period_of_report") and hasattr(item, "accession_number") for item in result
        )

    def test_returns_empty_list_when_company_throws(self, mocker):
        """예외1. edgartools 호출 중 예외가 발생할 때 -> 빈 리스트 반환"""
        mocker.patch("app.modules.past_filings.fetcher.Company", side_effect=Exception("boom"))

        result = fetcher.fetch_past_20_quarters_filings_info("0000000000")

        assert result == []

"""
단위 테스트 코드
1. get_existing_filings
    정상1. 회사 ID에 해당하는 Filing이 있을 때 -> 해당 Filing 리스트 반환
    정상2. 해당 회사 ID에 Filing이 없을 때 -> 빈 리스트 반환

2. bulk_save_original_filings
    정상1. original_filings 리스트가 정상일 때 -> filing_crud.bulk_create_filings가 호출되어 생성된 리스트 반환
    예외1. original_filings가 None일 때 -> filing_crud.bulk_create_filings 호출 시 TypeError 또는 pydantic.ValidationError 발생 가능

3. bulk_save_amendment_filings
    정상1. amendment_filings이 비어 있을 때 -> 아무 작업도 하지 않음
    정상2. amendment_filings에 항목이 있을 때 -> filing_crud.bulk_create_filings가 호출되어 저장

4. commit_filings
    정상1. db.commit 호출

5. rollback_filings
    정상1. db.rollback 호출
"""

from app.modules.past_filings import repository


class TestGetExistingFilings:
    def test_returns_existing_filings(self, mocker):
        """정상1. 회사 ID에 해당하는 Filing이 있을 때 -> 해당 Filing 리스트 반환"""
        query = mocker.Mock()
        query.filter.return_value.all.return_value = ["filing1", "filing2"]
        db = mocker.Mock()
        db.query.return_value = query

        result = repository.get_existing_filings(db, company_id=1)

        db.query.assert_called_once()
        query.filter.assert_called_once()
        assert result == ["filing1", "filing2"]

    def test_returns_empty_list_when_no_filings(self, mocker):
        """정상2. 해당 회사 ID에 Filing이 없을 때 -> 빈 리스트 반환"""
        query = mocker.Mock()
        query.filter.return_value.all.return_value = []
        db = mocker.Mock()
        db.query.return_value = query

        result = repository.get_existing_filings(db, company_id=1)

        assert result == []


class TestBulkSaveOriginalFilings:
    def test_calls_bulk_create_filings_and_returns_result(self, mocker):
        """정상1. original_filings 리스트가 정상일 때 -> filing_crud.bulk_create_filings가 호출되어 생성된 리스트 반환"""
        db = mocker.Mock()
        original_filings = ["f1", "f2"]
        patched = mocker.patch(
            "app.modules.past_filings.repository.filing_crud.bulk_create_filings",
            return_value=["saved1", "saved2"],
        )

        result = repository.bulk_save_original_filings(db, original_filings)

        patched.assert_called_once_with(db, original_filings)
        assert result == ["saved1", "saved2"]


class TestBulkSaveAmendmentFilings:
    def test_does_nothing_when_amendment_filings_empty(self, mocker):
        """정상1. amendment_filings이 비어 있을 때 -> 아무 작업도 하지 않음"""
        patched = mocker.patch("app.modules.past_filings.repository.filing_crud.bulk_create_filings")

        repository.bulk_save_amendment_filings(mocker.Mock(), [])

        patched.assert_not_called()

    def test_calls_bulk_create_filings_when_amendment_filings_present(self, mocker):
        """정상2. amendment_filings에 항목이 있을 때 -> filing_crud.bulk_create_filings가 호출되어 저장"""
        db = mocker.Mock()
        amendment_filings = ["a1"]
        patched = mocker.patch("app.modules.past_filings.repository.filing_crud.bulk_create_filings")

        repository.bulk_save_amendment_filings(db, amendment_filings)

        patched.assert_called_once_with(db, amendment_filings)


class TestCommitAndRollbackFilings:
    def test_commit_calls_db_commit(self, mocker):
        """정상1. db.commit 호출"""
        db = mocker.Mock()

        repository.commit_filings(db)

        db.commit.assert_called_once()

    def test_rollback_calls_db_rollback(self, mocker):
        """정상1. db.rollback 호출"""
        db = mocker.Mock()

        repository.rollback_filings(db)

        db.rollback.assert_called_once()

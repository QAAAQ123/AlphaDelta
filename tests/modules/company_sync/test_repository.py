"""
repository 단위 테스트 항목
5. _build_company_create   
    정상
    1. 정상 인자가 들어왔을 때 -> Company DTO 리턴
6. _persist_company DB 실제 저장 이외
    에러
    1. IntegrityError 발생 시 → rollback() 호출 + raise
    2. SQLAlchemyError 발생 시 → rollback() 호출 + raise
    정상
    1. 정상 인자가 들어왔을 때 -> company(Company) 리턴
        - 단순히 company를 return하는지만 검사
        실제 DB에 저장하는 것은 통합 테스트에서
"""

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.base import Quarter
from app.schemas import CompanyCreate
from app.modules.company_sync.repository import build_company_create, persist_company


class TestBuildCompanyCreate:
    """build_company_create 단위 테스트"""

    def test_build_company_create_returns_company_dto(self):
        """정상1. 정상 인자가 들어왔을 때 -> Company DTO 리턴"""
        # given-상황
        ticker = "AAPL"
        company_data = {
            "company": "Apple Inc.",
            "industry": "Technology",
            "subsector": "Consumer Electronics",
        }
        cik_fiscal_dict = {
            "cik": "0000320193",
            "fiscal_year_end": Quarter.Q4,
        }

        # when-실행
        result = build_company_create(ticker, company_data, cik_fiscal_dict)

        # then-결과 확인
        assert isinstance(result, CompanyCreate)
        assert result.ticker == ticker
        assert result.name == "Apple Inc."
        assert result.cik == "0000320193"
        assert result.industry == "Technology"
        assert result.sector == "Consumer Electronics"
        assert result.fiscal_year_end == Quarter.Q4


class TestPersistCompany:
    """persist_company 단위 테스트"""

    def test_persist_company_commits_and_returns_company(self, mocker):
        """정상1. 정상 인자가 들어왔을 때 -> company(Company) 리턴"""
        # given-상황
        db = mocker.Mock()
        company = mocker.Mock()

        # when-실행
        result = persist_company(db, company)

        # then-결과 확인
        db.add.assert_called_once_with(company)
        db.commit.assert_called_once()
        assert result is company

    def test_persist_company_rolls_back_and_raises_integrity_error(self, mocker):
        """에러1. IntegrityError 발생 시 → rollback() 호출 + raise"""
        # given-상황
        db = mocker.Mock()
        company = mocker.Mock()
        db.commit.side_effect = IntegrityError("stmt", "params", "orig")

        # when-실행
        with pytest.raises(IntegrityError):
            persist_company(db, company)

        # then-결과 확인
        db.rollback.assert_called_once()
        db.add.assert_called_once_with(company)
        db.commit.assert_called_once()

    def test_persist_company_rolls_back_and_raises_sqlalchemy_error(self, mocker):
        """에러2. SQLAlchemyError 발생 시 → rollback() 호출 + raise"""
        # given-상황
        db = mocker.Mock()
        company = mocker.Mock()
        db.commit.side_effect = SQLAlchemyError("commit failed")

        # when-실행
        with pytest.raises(SQLAlchemyError):
            persist_company(db, company)

        # then-결과 확인
        db.rollback.assert_called_once()
        db.add.assert_called_once_with(company)
        db.commit.assert_called_once()
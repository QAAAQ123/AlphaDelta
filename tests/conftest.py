import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db_session() -> MagicMock:
    """DB에 실제로 붙지 않는 순수 Mock 세션. 대부분의 단위 테스트에서 사용."""
    return MagicMock(spec=Session)
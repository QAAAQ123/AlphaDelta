import pytest


@pytest.fixture(scope="module")
def vcr_config():
    return {
        # 민감할 수 있는 헤더 제거 (User-Agent엔 보통 이메일이 들어감)
        "filter_headers": [
            ("User-Agent", "test-agent contact@example.com"),
            ("Authorization", "DUMMY"),
        ],
        # 요청 매칭 기준 - URL, method만 봐도 충분 (query까지 보고 싶으면 추가)
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        # 카세트 저장 위치
        "cassette_library_dir": "tests/cassettes",
        # 기록 모드: 처음엔 "once", 이후엔 CI에서 "none"으로 고정 추천
        "record_mode": "once",
    }


@pytest.fixture(scope="module")
def vcr_cassette_dir(request):
    return f"tests/cassettes/{request.module.__name__}"
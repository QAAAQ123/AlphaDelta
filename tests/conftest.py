import pytest


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [
            ("User-Agent", "test-agent contact@example.com"),
            ("Authorization", "DUMMY"),
        ],
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "record_mode": "once",
    }


@pytest.fixture(scope="module")
def vcr_cassette_dir(request):
    return f"tests/cassettes/{request.module.__name__}"
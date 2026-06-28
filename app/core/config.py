import sys
from loguru import logger
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

class Settings(BaseSettings):
    # API 및 프로젝트 정보 기본값 세팅
    #PROJECT_NAME: str = "Disclosure Fact & Context Analyzer"
    #API_V1_STR: str = "/api"

    # 데이터베이스 URL (Pydantic이 주입받을 때 엄격하게 문자열 검증)
    DATABASE_URL: str = "postgresql://postgres:postgres_dev123@db:5432/disclosure_dev_db"

    #GOOGLE_AI_API_KEY: str  # 6~7단계 Google AI Studio 연동용

    # 외부 환경 변수(.env 파일 및 컨테이너 environment) 자동 매핑 설정
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # 컨테이너 내부에 시스템 환경변수가 더 많아도 에러 내지 말고 필요한 것만 파싱
    )

def setup_global_mdc_logging():
    #앱 전역 MDC 로깅 포맷 설정
    logger.remove()
    log_format = (
    "{time:YYYY/MM/DD HH:mm:ss}|"
    "<level>{level:<8}</level>|"
    "[Ticker:{extra[ticker]:<5}]|[RequestID:{extra[request_id]:<8}]|[Domain:{extra[domain]:<6}] - "
    "<level>{message}</level>"
    )   

    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "format": log_format,
                "level": "DEBUG"
            }
        ],
        patcher=lambda record: (
            record["extra"].update({"request_id": _request_id.get()}),
            record["extra"].setdefault("ticker", "-"),
            record["extra"].setdefault("domain", "SYSTEM")
        )
    )

# 전역에서 이 인스턴스를 import하여 싱글톤처럼 재사용합니다.
settings = Settings()
setup_global_mdc_logging()

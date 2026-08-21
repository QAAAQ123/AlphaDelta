"""
로깅 설정 모듈.
이 모듈은 애플리케이션에서 단 한 번, 가장 먼저 import되어야 합니다.
다른 모든 모듈은 `from config.logger import logger` 로만 사용하세요.

사용 예시:
with logger.contextualize(domain="USER", user_id=123, request_id="abc"):
    logger.info("처리 시작")   # → [USER] user_id=123 request_id=abc - 처리 시작
    some_function()
"""
import sys
#from pathlib import Path
from loguru import logger

#LOG_DIR = Path("logs")
#LOG_DIR.mkdir(exist_ok=True)

logger.remove()

# format 함수에서 제외할 예약 필드 (domain은 별도로 표시하므로)
_RESERVED_KEYS = {"domain"}


def dynamic_format(record: dict) -> str:
    domain = record["extra"].get("domain", "SYSTEM")

    # domain을 제외한 extra 필드들을 key=value 형태로 동적 조립
    context_pairs = [
        f"{key}={value}"
        for key, value in record["extra"].items()
        if key not in _RESERVED_KEYS and value is not None
    ]
    context_str = " ".join(context_pairs) if context_pairs else "-"

    # loguru format 함수는 record에 값을 써넣고, 포맷 문자열을 반환해야 함
    record["extra"]["_domain"] = domain
    record["extra"]["_context"] = context_str

    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green>|"
        "<level>{level:<8}</level>|"
        "[{extra[_domain]}] {extra[_context]} - "
        "<level>{message}</level>\n{exception}"
    )


logger.configure(extra={"domain": "SYSTEM"})

# 콘솔
logger.add(
    sys.stdout,
    format=dynamic_format,
    level="DEBUG",
    colorize=True,
    backtrace=True,
    diagnose=True,   # 운영 배포시 False로 전환
)

# # 전체 이력 파일
# logger.add(
#     LOG_DIR / "app_{time:YYYY-MM-DD}.log",
#     format=dynamic_format,
#     level="DEBUG",
#     rotation="1 day",
#     retention="30 days",
#     compression="zip",
#     encoding="utf-8",
#     enqueue=True,
# )

# # 에러 전용 파일
# logger.add(
#     LOG_DIR / "errors_{time:YYYY-MM-DD}.log",
#     format=dynamic_format,
#     level="ERROR",
#     rotation="1 day",
#     retention="90 days",
#     encoding="utf-8",
#     enqueue=True,
# )

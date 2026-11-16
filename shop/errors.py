"""DB 오류를 한 곳에서 번역한다."""

from functools import wraps

from postgrest.exceptions import APIError

PG_ERRORS = {
    "23502": "필수 값 누락 (NOT NULL)",
    "23503": "참조 무결성 위반 (FK) — 없는 대상을 가리키거나 아직 참조 중인 행",
    "23505": "중복 값 (UNIQUE)",
    "23514": "허용 범위 위반 (CHECK)",
    "42501": "권한 없음 (RLS 정책 또는 열 GRANT)",
    "P0001": "비즈니스 규칙 위반 (RPC 함수가 거부)",
}

class ServiceError(Exception):
    """앱 계층의 단일 예외. code 로 분기하고(예: 23503 → 소프트 삭제), message 는 사람이 읽는다."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code

def db_errors(fn):
    """서비스 메서드를 감싸 APIError 를 ServiceError 로 바꾸는 데코레이터."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except APIError as error:
            label = PG_ERRORS.get(error.code, "DB 오류")
            raise ServiceError(f"[{error.code}] {label}: {error.message}", error.code) from error

    return wrapper

def first_or_error(rows: list, what: str) -> dict:
    """UPDATE·DELETE·조회 결과가 비었을 때의 처리."""
    if not rows:
        raise ServiceError(f"{what}: 대상이 없거나 권한이 없습니다.")
    return rows[0]

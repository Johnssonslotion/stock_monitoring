"""
API Hub 예외 클래스

모든 API Client에서 사용하는 공통 예외를 정의합니다.
"""


class APIError(Exception):
    """API 호출 실패 기본 예외"""
    pass


class RateLimitError(APIError):
    """Rate Limit 초과 (429 에러)"""
    pass


class AuthenticationError(APIError):
    """인증 실패 (401, 403 에러)"""
    pass


class NetworkError(APIError):
    """네트워크 오류 (연결 실패, 타임아웃 등)"""
    pass


class ValidationError(APIError):
    """응답 데이터 검증 실패"""
    pass

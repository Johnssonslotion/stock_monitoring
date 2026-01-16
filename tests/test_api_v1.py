import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import os

# API_AUTH_SECRET를 환경변수에서 가져오거나 기본값 사용
API_AUTH_SECRET = os.getenv("API_AUTH_SECRET", "super-secret-key")

def test_health_check():
    """헬스체크 API 검증"""
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "degraded", "unhealthy"]

def test_unauthorized_missing_header():
    """인증 헤더 누락 시 422 에러 (FastAPI 기본 동작) 검증"""
    with TestClient(app) as client:
        response = client.get("/api/v1/ticks/AAPL")
        # Header(...) 필수 필드 누락 시 FastAPI는 422 반환
        assert response.status_code == 422

def test_unauthorized_wrong_key():
    """잘못된 API Key 제공 시 403 에러 검증"""
    with TestClient(app) as client:
        response = client.get("/api/v1/ticks/AAPL", headers={"x-api-key": "wrong-key"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid API Key"

def test_authorized_access_flow():
    """정상 인증 시 응답 상태 검증 (DB 연결 여부에 따라 200 또는 503)"""
    with TestClient(app) as client:
        response = client.get("/api/v1/ticks/AAPL", headers={"x-api-key": API_AUTH_SECRET})
        
        # 통합 테스트 환경에서 DB 연결이 성공하면 200, 실패하면 503
        # 여기서는 최소한 403(인증에러)이나 422(파라미터에러)는 아니어야 함
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            assert isinstance(response.json(), list)
        else:
            assert response.json()["detail"] == "Database not available"

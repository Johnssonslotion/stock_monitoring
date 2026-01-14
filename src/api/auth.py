from fastapi import Header, HTTPException
import os

API_AUTH_SECRET = os.getenv("API_AUTH_SECRET", "super-secret-key")

async def verify_api_key(x_api_key: str = Header(..., alias="x-api-key")):
    """API-Key 기반 보안 인증 미들웨어"""
    if x_api_key != API_AUTH_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

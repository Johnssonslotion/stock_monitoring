# Rate Limiter 통합 계획 문서

**Document ID**: ISSUE-037-D  
**Author**: Infrastructure Persona  
**Date**: 2026-01-23  
**Reviewers**: Infra + PM  

---

## 1. 개요

Hub v2 Worker와 redis-gatekeeper 통합하여 API Rate Limit을 준수합니다.

---

## 2. redis-gatekeeper 통합 방식

### 2.1 Gatekeeper 호출

```python
async def acquire_token(provider: str) -> bool:
    """Rate Limiter 토큰 획득"""
    result = await redis.eval(
        RATE_LIMIT_SCRIPT,
        keys=[f"rate:limit:{provider}"],
        args=[1, 10]  # 초당 10회
    )
    return result == 1  # 1 = 허용, 0 = 거부
```

### 2.2 Multi-Worker 조율

- 모든 Worker가 동일한 Redis Key 사용
- gatekeeper가 전역 Rate Limit 추적
- Worker는 토큰 획득 실패 시 대기 (exponential backoff)

---

## 3. 보안: Token 암호화 (Optional)

**Phase 2**: 평문 저장 허용  
**Phase 3**: Fernet 암호화 검토

---

**Review Status**: ⏳ Pending  
**Implementation**: 1-2 hours

# 보안 가이드라인 (Security Guidelines)

## 1. API Key 관리 원칙
주식/코인 트레이딩 시스템은 자산을 다루므로 금융 보안 수준의 관리가 필요하다.

### 1.1 절대 금지 (Never)
-   **소스 코드에 키 하드코딩**: `api_key = "x8s..."` -> **적발 시 즉시 퇴출**.
-   **Git에 `.env` 파일 커밋**: `.gitignore`에 반드시 포함되어야 함.
-   **단톡방/메신저로 키 전송**: 평문 전송 금지.

### 1.2 권장 사항 (Recommended)
-   **.env.example 활용**: 실제 키는 없지만 필요한 변수명만 적힌 템플릿 제공.
-   **환경 변수 주입**: Docker 실행 시 `--env-file` 또는 CI/CD 파이프라인의 `Secrets` 사용.
-   **최소 권한 원칙**: 거래소 API Key 발급 시 '출금(Withdraw)' 권한은 절대 켜지 않는다. 오직 '조회(Read)'와 '주문(Order)'만 허용.

## 2. 개인정보 및 로그 보안
-   **PII**: 사용자 이름, 전화번호 등은 로그에 남기지 않는다.
-   **Log masking**: API Key나 비밀번호가 로그에 찍히지 않도록 마스킹 처리한다.
    -   *Bad*: `logger.info(f"Using key: {api_key}")`
    -   *Good*: `logger.info(f"Using key: {api_key[:4]}***")`

## 3. 네트워크 보안
-   **Redis**: 기본적으로 `bind 127.0.0.1`로 설정하여 외부 접속 차단.
-   **Firewall**: 오라클 클라우드 Security List에서 불필요한 Inbound 포트(예: Redis 6379, DB 포트)는 0.0.0.0에 개방하지 않는다.

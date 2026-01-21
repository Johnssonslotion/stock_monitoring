# 키움 API 접근 문제 진단 결과

**날짜**: 2026-01-19  
**문제**: 키움 OAuth2 토큰 발급 실패 (HTTP 400 "Request Blocked")

## 테스트 결과

### 테스트 환경
- ✅ 로컬 환경 테스트 완료
- ✅ 컨테이너 환경 테스트 완료  
- ✅ 양쪽 엔드포인트 테스트 완료

### 테스트 결과
| 환경 | 엔드포인트 | 결과 |
|------|-----------|------|
| 로컬 | `https://openapi.kiwoom.com/oauth2/token` | ❌ HTTP 400 Request Blocked |
| 로컬 | `https://mockapi.kiwoom.com/oauth2/token` | ❌ HTTP 400 Request Blocked |
| 컨테이너 | `https://openapi.kiwoom.com/oauth2/token` | ❌ HTTP 400 Request Blocked |

## 결론

### ✅ 확인된 사항
1. **IP 차단 아님** - 로컬/컨테이너 동일한 오류
2. **네트워크 정상** - 요청이 서버에 도달함
3. **엔드포인트 정확함** - openapi/mockapi 도메인 확인됨
4. **요청 형식 정확함** - JSON body, Content-Type 헤더 정확

### ❌ 문제 원인 (추정)
1. **APP_KEY/SECRET 문제**
   - 잘못된 인증 정보
   - 만료된 키
   - 폐기된 키

2. **API 서비스 해지**
   - 3개월 미사용으로 인한 자동 해지
   - 키움 API+ 서비스 미신청 또는 승인 대기

3. **계정 제한**
   - 계정 정지 또는 제한
   - 서비스 약관 위반

## 필요 조치

### 🔴 즉시 필요 (사용자 액션)
1. **키움증권 개발자 포털 확인**
   - URL: https://apiportal.kiwoom.com 또는 https://openapi.kiwoom.com
   - API 사용 신청 상태 확인
   - APP_KEY, APP_SECRET 재확인

2. **API 서비스 상태 확인**
   - Open API+ 서비스 활성화 여부
   - 최근 접속 이력 (3개월 미접속 시 해지됨)
   - 서비스 신청/재신청 필요 여부

3. **인증 정보 재발급**
   - APP_KEY 재발급
   - APP_SECRET 재발급
   - `.env` 파일 업데이트

### 🟡 대안
- **KIS API 사용** - 현재 KIS는 정상 동작 중
- **데이터 소스 우선순위 재조정** - KIS 우선, 키움 백업으로 변경

## 참고 문서
- `src/data_ingestion/price/kr/kiwoom_ws.py` - 현재 구현
- `.env` - 환경 변수 (APP_KEY, APP_SECRET)
- 키움 API 가이드: https://autostock.tistory.com/167

## 다음 단계
1. 사용자가 키움 개발자 포털에서 API 상태 확인
2. 유효한 APP_KEY/SECRET 확보
3. 코드 업데이트 (엔드포인트 수정 필요)
   - ❌ 잘못된: `https://api.kiwoom.com/oauth2/token`
   - ✅ 올바른: `https://openapi.kiwoom.com/oauth2/token` (실계좌)
   - ✅ 올바른: `https://mockapi.kiwoom.com/oauth2/token` (모의투자)

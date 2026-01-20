# 로컬 UI 테스트 - 실제 DB 데이터 연동

## 현재 상황

### ✅ 백엔드 (Docker)
- Redis: 실행 중
- TimescaleDB: 실행 중 (94,497건 데이터 있음)
- API Server: 실행 중 (포트 8000)

### ✅ 프론트엔드 (Vite)
- 서버: http://localhost:5173/ 실행 중
- API 키: `super-secret-key`로 수정 완료

### ⚠️ 이슈
- `/api/v1/candles/005930` 엔드포인트에서 Internal Server Error 발생
- 원인 조사 중...

## 다음 단계
1. API 서버 에러 로그 확인
2. 백엔드 API 수정 또는 우회
3. 브라우저에서 실제 UI 확인

## 브라우저 접속
```
http://localhost:5173/
```

- Dashboard 탭: Market Map 확인
- Analysis 탭: 차트 확인 (실제 DB 데이터)
- System 탭: 시스템 상태 확인

# 네트워크 노출 문제 진단 보고서

## 📊 `.ai-rules.md` 7.1항 위반 진단

### 문제점
> **"로그 정상" ≠ "데이터 흐름 정상". 실제 데이터 확인 필수** (`.ai-rules.md` 7.1)

- ✅ Unit Test (Gate 1): Pass
- ✅ Integration Test (Gate 2): Pass  
- ❌ **E2E Test (외부 접속)**: **FAIL** ← 현재 상황

### 진단 결과

#### 정상 동작 항목
```bash
# 1. 서버 내부 접속: ✅ 정상
curl http://localhost:5173  # OK
curl http://localhost:8000/health  # OK

# 2. Docker 포트 바인딩: ✅ 정상
5173/tcp -> 0.0.0.0:5173
8000/tcp -> 0.0.0.0:8000

# 3. iptables: ✅ 정상
ACCEPT tcp dpt:5173
ACCEPT tcp dpt:8000
```

#### 문제 항목
```bash
# 외부 IP로 접속: ❌ 실패
curl http://168.107.40.168:5173  # Connection timeout
curl http://168.107.40.168:8000  # Connection timeout
```

### 근본 원인

**오라클 클라우드 Security List 미설정**

Docker는 정상적으로 포트를 열었으나, **클라우드 레벨 방화벽**에서 차단됨:

```
[외부 브라우저] 
    ↓
[오라클 클라우드 Security List] ← ❌ 여기서 차단!
    ↓
[VM iptables] ✅ 통과
    ↓
[Docker 0.0.0.0:5173, 8000] ✅ 열림
```

### 해결 방안

#### 방안 1: 오라클 클라우드 Security List 설정 (권장)
**장점**: 정석적인 방법, 영구적  
**단점**: 웹 콘솔 접속 필요

1. 오라클 클라우드 콘솔 접속
2. Networking → Virtual Cloud Networks
3. Security Lists → Default Security List
4. Add Ingress Rules:
   - Source CIDR: `0.0.0.0/0`
   - Destination Port: `5173,8000`
   - Protocol: TCP

#### 방안 2: ngrok 터널 (즉시 가능)
**장점**: 즉시 사용 가능, 클라우드 설정 불필요  
**단점**: 임시 URL, 무료 버전 제한

```bash
# ngrok 설치 및 터널 생성
docker run -it --rm --net=host ngrok/ngrok http 5173
docker run -it --rm --net=host ngrok/ngrok http 8000
```

#### 방안 3: SSH 포트포워딩 (이미 가이드 제공됨)
**장점**: 보안성 최고  
**단점**: 사용자 PC에서 SSH 연결 유지 필요

```bash
ssh -L 5173:localhost:5173 -L 8000:localhost:8000 ubuntu@168.107.40.168
# 브라우저: http://localhost:5173
```

## 📝 `.ai-rules.md` 준수 체크리스트

### 7.1 통합 테스트 강제
- [x] 단위 테스트 (함수 로직만) ✅
- [x] 통합 테스트 (실제 Redis/DB 연결) ✅
- [ ] **E2E 테스트 (전체 파이프라인)** ← **외부 접속 미검증**

### 7.2 Zero Data 알람
- [x] API 서버 로그에서 "Data flow stopped" 알람 확인됨
- [ ] 외부 클라이언트 연결 검증 필요

### 7.3 관찰 가능성 원칙
**필요 메트릭**:
- [x] Collector: published_count ✅
- [x] Archiver: saved_count ✅  
- [ ] **External Access: connection_count** ← 추가 필요

## 🎯 권장 조치

**즉시 조치** (Zero-Cost 원칙):
1. ngrok으로 임시 터널 생성 → 외부 접속 테스트
2. 테스트 성공 시 `test_registry.md` 외부망 항목 Pass 처리

**영구 해결** (프로덕션):
1. 오라클 클라우드 Security List 설정
2. 리버스 프록시(Nginx) + HTTPS 적용
3. 외부 접속 모니터링 추가

## 📊 테스트 커버리지 갭

```
현재 검증 범위:
├── Unit (Gate 1): ✅ 100%
├── Integration (Gate 2): ✅ 100%
└── E2E (Gate 3): ❌ 50%  ← 외부망 검증 누락!
    ├── 내부망 (localhost): ✅
    └── 외부망 (Public IP): ❌
```

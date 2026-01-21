# CI/CD 배포 전략 (Deployment Strategy)

## 📋 개요 (Overview)

이 프로젝트는 **브랜치 기반 자동 배포 전략**을 사용합니다.
- **Production (`main`)**: 최종 릴리즈 버전
- **Development (`develop`)**: 실시간 개발/테스트 환경
- **Feature Branches**: CI 임시 컨테이너로 격리 테스트

---

## 🏗️ 서버 폴더 구조 (Server Directory Structure)

**중요**: 현재 프로젝트는 **단일 운영 환경**을 사용합니다.

```bash
oracle-a1:/home/ubuntu/workspace/
├── stock_monitoring/     # develop 브랜치 운영 (실제 Production)
│   ├── .env             # APP_ENV=production
│   ├── data/            # 운영 데이터
│   └── logs/
│
└── stock_dev/           # 실험/테스트용 (배포 대상 아님)
    └── (자유롭게 브랜치 변경/테스트)
```

---

## 🔄 브랜치별 배포 정책 (Branch Deployment Policy)

### 브랜치 역할 정의

| 브랜치 | 배포 대상 | 용도 | CD 트리거 |
|:---|:---|:---|:---:|
| **`develop`** | `oracle-a1:/workspace/stock_monitoring` | **실제 운영 서버** | ✅ |
| **`main`** | ❌ 배포 안 됨 | 버전 아카이브 (v1.0.0 태깅용) | ❌ |
| **`feat/*`, `fix/*`, `test/*`** | ❌ 배포 안 됨 | CI 테스트만 (임시 컨테이너) | ❌ |

### 워크플로우

```
로컬 작업:
  feat/new-feature (브랜치 생성)
     ↓ (개발 완료)
  git push origin feat/new-feature
     ↓ (CI 테스트만 실행)
  
GitHub:
  Pull Request 생성 (feat/* → develop)
     ↓ (리뷰/승인)
  Merge to develop
     ↓ (🚀 CD 트리거!)
  
운영 서버:
  oracle-a1:/workspace/stock_monitoring
     ↓ (자동 배포)
  git pull origin develop
  docker compose up -d --build
     ✅ 운영 반영 완료

버전 관리 (선택):
  develop → main PR (안정화 후)
     ↓ (태깅)
  GitHub Release v1.2.3
     ✅ 아카이브 완료 (배포는 안 됨)
```

---

## 🚨 배포 안전 수칙

1. **절대 금지**: `stock_monitoring` 폴더에서 직접 코드 수정
   - Git pull conflict 발생 → 배포 실패
   - 실험은 반드시 `stock_dev` 폴더 사용

2. **안전한 서버 작업**:
   ```bash
   # ✅ 권장: stock_dev에서 실험
   cd ~/workspace/stock_dev
   git checkout -b hotfix/emergency
   # 수정/테스트 후
   git push origin hotfix/emergency
   # → PR → develop 머지 → 자동 배포
   
   # ❌ 금지: stock_monitoring 직접 수정
   cd ~/workspace/stock_monitoring
   vi src/file.py  # 절대 금지!
   ```

3. **롤백 절차**:
   ```bash
   # 배포 후 문제 발생 시
   cd ~/workspace/stock_monitoring
   git log --oneline -5  # 이전 커밋 확인
   git reset --hard <이전커밋해시>
   docker compose restart
   ```

---

## 🚀 CI/CD 워크플로우 상세 (Workflow Details)

### 1. CI (Quality Check) - 모든 브랜치
**트리거**: `push`, `pull_request`  
**실행 위치**: GitHub Actions 클라우드 (임시 Runner)  
**동작**:
```yaml
on: [push, pull_request]
jobs:
  quality-check:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
      timescaledb:
        image: timescale/timescaledb:latest-pg16
    steps:
      - Checkout 코드
      - Poetry 설치 및 의존성 설치
      - Black, Isort 린트
      - Pytest 실행 (임시 DB/Redis 사용)
```

**결과**: 통과/실패만 확인, 서버에 영향 없음.

---

### 2. CD (Deploy) - `main`, `develop` 브랜치만

#### 2.1 `develop` → `stock_dev` 배포
**트리거**: `push: branches: ["develop"]`  
**실행 위치**: GitHub Actions → SSH → `oracle-a1:/workspace/stock_dev`  
**동작**:
```bash
cd ~/workspace/stock_dev
git fetch origin
git checkout develop
git pull origin develop
docker compose -f deploy/docker-compose.yml --profile dev up -d --build
```

**환경 변수 주입**:
```bash
# stock_dev/.env
APP_ENV=development
DB_NAME=stockval_dev
REDIS_DB=1
```

#### 2.2 `main` → `stock_prod` 배포
**트리거**: `push: branches: ["main"]`  
**실행 위치**: GitHub Actions → SSH → `oracle-a1:/workspace/stock_prod`  
**동작**:
```bash
cd ~/workspace/stock_prod
git fetch origin
git checkout main
git pull origin main
docker compose -f deploy/docker-compose.yml --profile real up -d --build
```

**환경 변수 주입**:
```bash
# stock_prod/.env
APP_ENV=production
DB_NAME=stockval
REDIS_DB=0
```

---

## 🧪 Feature Branch 테스트 전략

**원칙**: Feature 브랜치는 **서버에 배포되지 않으며**, CI 환경에서만 테스트됩니다.

### 테스트 흐름
```
개발자 → feat/new-feature 푸시
   ↓
GitHub Actions CI 트리거
   ↓
임시 Ubuntu Runner 생성
   ↓
Redis, TimescaleDB 서비스 컨테이너 시작 (GitHub Services)
   ↓
pytest 실행 (임시 DB 사용)
   ↓
통과 → PR 승인 가능
실패 → 코드 수정 필요
   ↓
PR 머지 → develop
   ↓
CD 트리거 → stock_dev 배포
```

---

## 📝 Workflow 파일 구조

### `.github/workflows/ci-check.yml`
```yaml
name: Quality Check
on: [push, pull_request]
# 모든 브랜치에서 실행
# Services: redis, timescaledb (임시)
```

### `.github/workflows/cd-deploy.yml`
```yaml
name: CD Deploy
on:
  push:
    branches: ["main", "develop"]

jobs:
  deploy:
    steps:
      - name: Deploy to Server
        run: |
          if [[ "${{ github.ref_name }}" == "main" ]]; then
            DEPLOY_DIR="stock_prod"
          else
            DEPLOY_DIR="stock_dev"
          fi
          
          ssh oracle-a1 "cd ~/workspace/${DEPLOY_DIR} && \
            git pull origin ${{ github.ref_name }} && \
            docker compose up -d --build"
```

---

## ✅ 환경 변수 체크리스트

### 필수 `.env` 변수 (모든 환경)
```bash
# API Keys (서버 폴더별로 독립 관리)
KIS_APP_KEY=xxxxx
KIS_APP_SECRET=xxxxx

# Environment Identifier
APP_ENV=production  # 또는 development

# Database
DB_HOST=stock-timescale
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=stockval  # prod: stockval, dev: stockval_dev

# Redis
REDIS_URL=redis://stock-redis:6379/0  # prod: /0, dev: /1
```

---

## 🎯 권장 작업 흐름 (Recommended Workflow)

### 로컬 개발 (Mac)
```bash
git checkout -b feat/my-feature
# 코드 수정
git push origin feat/my-feature
# CI 자동 실행 (임시 컨테이너)
# PR 생성 → 리뷰 → develop 머지
```

### 개발 서버 테스트
```bash
# develop 머지 시 자동 배포됨
# 확인: http://oracle-a1:8001 (stock_dev)
```

### 프로덕션 릴리즈
```bash
# develop → main PR 생성
# 릴리즈 노트 작성 후 머지
# 자동 배포: http://oracle-a1:8000 (stock_prod)
```

---

## 🚨 주의사항 (Warnings)

1. **절대 금지**: `stock_prod`, `stock_dev` 폴더에서 직접 코드 수정
   - Git pull conflict 발생 → 배포 실패
2. **환경 변수 동기화**: `.env` 변경 시 수동 업데이트 필요
3. **포트 충돌**: 로컬 테스트 시 `docker-compose.local.yml` 사용
4. **데이터 분리**: `stock_dev` 데이터를 `stock_prod`로 복사 금지

---

## 📚 참고 문서
- [Infrastructure Rules](infrastructure.md)
- [Development Standards](development.md)
- [Master Roadmap](../strategy/master_roadmap.md)

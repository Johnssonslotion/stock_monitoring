# Database Migrations

> **마이그레이션 관리 시스템**  
> 프로덕션 DB 스키마 변경의 단일 진실 공급원 (Single Source of Truth)

---

## 📋 원칙

1. **모든 스키마 변경은 마이그레이션 파일로 관리**
2. **Python 코드에 DDL 금지** (검증만 허용)
3. **순차 번호 부여** (001, 002, 003, ...)
4. **Up/Down 스크립트 쌍** (롤백 가능)
5. **마이그레이션 전 백업 필수**

---

## 🚀 사용법

### 상태 확인
```bash
make migrate-status
# 또는
./scripts/db/migrate.sh status
```

**출력 예시:**
```
=== Migration Status ===

Database: stockval (Container: stock-timescale)

Applied Migrations:
  ✅ 20260116_085150 001_init_schema.sql
  ✅ 20260116_090230 002_add_orderbook.sql

Pending Migrations:
  ⏳ 003_add_timestamp_layers.sql
  ⏳ 004_normalize_tables.sql

Total: 2 applied, 2 pending
```

### 마이그레이션 적용
```bash
make migrate-up
# 또는
./scripts/db/migrate.sh up
```

**동작:**
1. 백업 생성 (`/tmp/db_pre_migration_YYYYMMDD_HHMMSS.sql`)
2. 마이그레이션 실행
3. 스키마 검증 (Deep Verification)
4. `.applied` 파일 업데이트

### 롤백
```bash
make migrate-down
# 또는
./scripts/db/migrate.sh down
```

**요구사항:** `XXX_migration_name_down.sql` 파일 필수

### 베이스라인 생성
```bash
make migrate-baseline
# 또는
./scripts/db/migrate.sh baseline
```

현재 프로덕션 스키마를 `000_baseline_TIMESTAMP.sql`로 저장

---

## 📁 파일 구조

```
migrations/
├── .applied                           # 적용 이력 (자동 생성)
├── README.md                          # 이 파일
├── 000_baseline_prod_schema.sql       # 2026-01-16 현재 프로덕션
├── 001_init_schema.sql                # 초기 스키마
├── 002_add_orderbook.sql              # 오더북 테이블 추가
├── 002_add_orderbook_down.sql         # 롤백 스크립트
├── 003_add_timestamp_layers.sql       # 타임스탬프 3계층 추가
├── 003_add_timestamp_layers_down.sql  # 롤백 스크립트
└── 004_normalize_tables.sql           # 다음 작업
```

---

## ✍️ 마이그레이션 작성 가이드

### 1. 파일명 규칙

```
{순서번호}_{설명}.sql
```

**예시:**
- `005_add_broker_column.sql`
- `006_create_trading_signals_table.sql`

### 2. 마이그레이션 파일 템플릿

**Up Migration** (`XXX_description.sql`):
```sql
-- Migration: {설명}
-- Description: {상세 설명}
-- Author: {작성자}
-- Date: {날짜}

-- ========================================
-- 1. 백업 확인 (주석)
-- ========================================
-- BACKUP REQUIRED: This migration modifies critical tables

-- ========================================
-- 2. 변경 사항
-- ========================================
ALTER TABLE market_ticks
    ADD COLUMN IF NOT EXISTS broker TEXT;

-- ========================================
-- 3. 인덱스 추가
-- ========================================
CREATE INDEX IF NOT EXISTS idx_market_ticks_broker
    ON market_ticks(broker);

-- ========================================
-- 4. 검증 쿼리 (주석)
-- ========================================
-- Verify: SELECT column_name FROM information_schema.columns WHERE table_name='market_ticks' AND column_name='broker';
```

**Down Migration** (`XXX_description_down.sql`):
```sql
-- Rollback: {설명}
-- Author: {작성자}
-- Date: {날짜}

-- ========================================
-- 역순으로 되돌리기
-- ========================================
DROP INDEX IF EXISTS idx_market_ticks_broker;

ALTER TABLE market_ticks
    DROP COLUMN IF EXISTS broker;
```

### 3. 주의사항

**✅ 권장:**
- `IF NOT EXISTS` / `IF EXISTS` 사용 (멱등성)
- 트랜잭션 단위로 작성
- 검증 쿼리 주석 포함

**❌ 금지:**
- 데이터 삭제 (`TRUNCATE`, `DELETE`) → 별도 승인 필요
- 외부 파일 참조 (self-contained)
- 환경별 분기 (단일 스크립트)

---

## 🔍 검증 프로세스

### 1. 로컬 테스트

```bash
# 백테스트 DB에서 테스트
docker-compose -f deploy/docker-compose.backtest.yml up -d
DB_CONTAINER=backtest-timescale DB_NAME=backtest_db ./scripts/db/migrate.sh up
```

### 2. 스키마 비교

```bash
# 기대 스키마와 실제 비교
docker exec stock-timescale psql -U postgres -d stockval -c "\d market_ticks"
```

### 3. Deep Verification (거버넌스 원칙)

```sql
-- 컬럼 존재 확인
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'market_ticks';

-- 인덱스 확인
SELECT indexname 
FROM pg_indexes 
WHERE tablename = 'market_ticks';

-- Hypertable 확인
SELECT * FROM timescaledb_information.hypertables 
WHERE hypertable_name = 'market_ticks';
```

---

## 🚨 트러블슈팅

### 문제: 마이그레이션이 실패했어요

```bash
# 1. 백업 위치 확인
ls -lh /tmp/db_pre_migration_*.sql

# 2. 에러 로그 확인
cat /tmp/migration.log

# 3. 수동 롤백
./scripts/db/migrate.sh down
```

### 문제: `.applied` 파일이 실제와 다릅니다

```bash
# 1. 현재 스키마 export
./scripts/db/migrate.sh baseline

# 2. .applied 초기화
rm migrations/.applied
# 재적용 필요 시
./scripts/db/migrate.sh up
```

### 문제: 롤백 스크립트가 없어요

**수동 롤백 절차:**
1. 백업 복원: `psql -U postgres -d stockval < /tmp/db_pre_migration_*.sql`
2. `.applied` 수동 편집
3. 다음부터 down 스크립트 작성

---

## 📚 참고 문서

- [Database Migration Strategy](../docs/governance/database_migration_strategy.md) - 전체 전략
- [Infrastructure Rules](../docs/governance/infrastructure.md) - DB 원칙
- [Development Guide](../docs/governance/development.md) - Git Flow

---

**Last Updated**: 2026-01-16  
**Maintainer**: Antigravity AI

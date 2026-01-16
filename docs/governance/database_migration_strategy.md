# Database Migration Strategy

> **작성일**: 2026-01-16  
> **상태**: 🔴 CRITICAL - 스키마 일관성 문제 발견  
> **목표**: 프로덕션 DB 직접 관리 + 중앙화된 마이그레이션 시스템 구축

---

## 1. 현황 분석 (2026-01-16)

### 1.1 프로덕션 DB 스키마 (Verified)

**컨테이너**: `stock-timescale` (Up 9 days)  
**DB**: `stockval` (TimescaleDB on PostgreSQL 16)

| 테이블 | 컬럼 수 | Hypertable | 인덱스 | Child Tables |
|--------|---------|------------|--------|--------------|
| `market_ticks` | 5 | ✅ | 1 | 3 |
| `market_orderbook` | 22 | ✅ | 1 | 2 |
| `market_candles` | 8 | ✅ | 2 (UNIQUE) | 107 |
| `market_minutes` | 7 | ✅ | 2 (UNIQUE) | 2 |
| `system_metrics` | 4 | ✅ | 1 | 2 |
| `data_quality_metrics` | 11 | ❌ | 3 | 0 |
| `symbol_metadata` | 10 | ❌ | 3 | 0 |

**총 데이터량**: 107개 candle chunks → 상당한 히스토리 축적

### 1.2 Python 코드 내 DDL 분산 현황

| 파일 | 테이블 | 일치 여부 |
|------|--------|-----------|
| [timescale_archiver.py](../../src/data_ingestion/archiver/timescale_archiver.py#L40) | `market_ticks` | ✅ 일치 |
| [timescale_archiver.py](../../src/data_ingestion/archiver/timescale_archiver.py#L59) | `system_metrics` | ✅ 일치 |
| [collector.py](../../src/data_ingestion/history/collector.py#L39) | `market_minutes` | ✅ 일치 |
| [loader.py](../../src/data_ingestion/history/loader.py#L122) | `market_candles` | ⚠️ UNIQUE 제약조건 누락 |
| [data_loader.py](../../src/backtest/data_loader.py#L49) | `market_ticks` | ✅ 일치 (백테스트용 중복) |

**🔴 발견된 문제:**

1. **DDL이 7개 Python 파일에 분산**
   - 신규 컬럼 추가 시 **일관성 유지 불가능**
   - Code Review 시 스키마 변경 추적 어려움

2. **마이그레이션 추적 시스템 부재**
   - `migrations/` 폴더에 1개 파일만 존재 (003_add_timestamp_layers.sql)
   - 실제 프로덕션에 **적용 여부 불명**
   - 롤백 불가능

3. **중요 테이블 누락**
   - `market_orderbook`: 22개 컬럼이지만 **Python 코드에 DDL 없음**
   - `data_quality_metrics`: 11개 컬럼 중 CHECK 제약조건 문서화 안됨
   - `symbol_metadata`: 메타데이터 관리 정책 불명

4. **migrations/003 적용 여부 불명**
   ```sql
   -- 003_add_timestamp_layers.sql에서 정의:
   ALTER TABLE market_ticks
       ADD COLUMN IF NOT EXISTS broker_time TIMESTAMPTZ,
       ADD COLUMN IF NOT EXISTS received_time TIMESTAMPTZ,
       ADD COLUMN IF NOT EXISTS sequence_number BIGINT;
   ```
   → 프로덕션 DB에는 **컬럼이 없음** (5개 컬럼만 존재)

---

## 2. 마이그레이션 전략

### 2.1 원칙 (Zero Cost + Data First)

1. **Single Source of Truth**: `migrations/` 폴더가 유일한 스키마 정의 장소
2. **No Code DDL**: Python 코드에서 `CREATE TABLE` 금지 (검증만 허용)
3. **Versioned & Tracked**: 모든 변경사항은 번호가 매겨진 마이그레이션 파일
4. **Rollback Ready**: Up/Down 스크립트 필수
5. **Deep Verification**: 마이그레이션 후 `SELECT`로 교차 검증

### 2.2 도구 선택: **파일 기반 마이그레이션 (Zero Cost)**

**선택**: Custom Bash Script (외부 도구 없이)

**이유**:
- Alembic: SQLAlchemy 의존성 (Python ORM 강제)
- Flyway: Java 설치 필요 (Oracle 프리티어 용량 부담)
- ✅ **Bash + psql**: 이미 TimescaleDB 컨테이너에 내장

**구현**:
```bash
# scripts/db/migrate.sh
#!/bin/bash
# Migration Tracker: migrations/.applied 파일에 적용 이력 저장
# Up: 순차 실행 / Down: 역순 롤백
```

### 2.3 마이그레이션 구조

```
migrations/
├── .applied                    # 적용된 마이그레이션 추적 파일
├── 000_baseline_prod_schema.sql  # 2026-01-16 현재 프로덕션 스키마
├── 001_init_schema.sql          # (이미 적용됨 - 추적용)
├── 002_add_orderbook.sql        # (이미 적용됨 - 추적용)
├── 003_add_timestamp_layers.sql # ⚠️ 미적용 (확인 필요)
├── 004_normalize_tables.sql     # 다음 작업
└── README.md                    # 마이그레이션 가이드
```

---

## 3. 즉시 실행 계획 (휴장 시간 활용)

### Phase 1: 현황 고정 (✅ DONE)

- [x] 프로덕션 스키마 export → `000_baseline_prod_schema.sql`
- [x] Python DDL 인벤토리 작성
- [x] 차이점 분석

### Phase 2: 마이그레이션 시스템 구축 (🔄 IN-PROGRESS)

1. **마이그레이션 스크립트 작성**
   ```bash
   make migrate-status  # 현재 적용된 마이그레이션 확인
   make migrate-up      # 미적용 마이그레이션 적용
   make migrate-down    # 마지막 마이그레이션 롤백
   ```

2. **과거 마이그레이션 역추적**
   - `market_orderbook` 생성 시점 확인
   - `data_quality_metrics` 정의 문서화

3. **003번 마이그레이션 검증**
   - 프로덕션에 적용할지 결정
   - 타임스탬프 3계층 필요성 재검토

### Phase 3: Python 코드 정리

1. **DDL 제거**
   ```python
   # Before
   await conn.execute("CREATE TABLE IF NOT EXISTS market_ticks ...")
   
   # After
   # 테이블이 없으면 에러 발생 → 마이그레이션 누락 알림
   result = await conn.fetchval("SELECT to_regclass('public.market_ticks')")
   if result is None:
       raise RuntimeError("Schema not initialized. Run migrations first.")
   ```

2. **스키마 검증 함수**
   ```python
   async def verify_schema(conn):
       """마이그레이션 적용 여부 확인"""
       expected_tables = ['market_ticks', 'market_orderbook', ...]
       for table in expected_tables:
           result = await conn.fetchval(f"SELECT to_regclass('public.{table}')")
           if result is None:
               raise RuntimeError(f"Table {table} not found. Run migrations.")
   ```

### Phase 4: 거버넌스 통합

1. **Development.md 업데이트**
   - 스키마 변경 시 마이그레이션 파일 필수
   - PR에 `migration-required` 라벨

2. **CI/CD 통합**
   - 테스트 환경 자동 마이그레이션
   - 프로덕션 배포 전 마이그레이션 체크

---

## 4. 리스크 관리

### 4.1 백업 전략

**규칙**: 마이그레이션 전 **필수 백업**

```bash
# 1. 스냅샷 백업 (Docker Volume)
docker run --rm -v stock-timescale-data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/db_backup_$(date +%Y%m%d_%H%M%S).tar.gz /data

# 2. 논리 백업 (SQL Dump)
docker exec stock-timescale pg_dump -U postgres -d stockval \
  > backups/stockval_$(date +%Y%m%d_%H%M%S).sql

# 3. 복구 테스트 (Dry-run)
docker-compose -f deploy/docker-compose.backtest.yml up -d
# 백업 복원 테스트
```

### 4.2 롤백 절차

```bash
# 1. 마이그레이션 롤백
make migrate-down

# 2. 데이터 손실 발생 시
docker stop stock-timescale
docker volume rm stock-timescale-data
tar xzf backups/db_backup_YYYYMMDD_HHMMSS.tar.gz
docker-compose up -d timescaledb
```

### 4.3 Doomsday Protocol 통합

**마이그레이션 실패 시 자동 대응**:
- Level 1: 롤백 시도
- Level 2: 백업에서 복원
- Level 3: Sentinel 알림 + 수동 개입

---

## 5. 다음 단계

### 즉시 (오늘 중)
- [ ] `scripts/db/migrate.sh` 구현
- [ ] `migrations/README.md` 작성
- [ ] 003번 마이그레이션 적용 여부 결정

### 단기 (1주일 이내)
- [ ] Python 코드에서 DDL 제거
- [ ] 스키마 검증 함수 추가
- [ ] Makefile에 migrate 명령어 통합

### 중기 (2주 이내)
- [ ] CI/CD 마이그레이션 체크 추가
- [ ] 거버넌스 문서 업데이트
- [ ] 팀 가이드 작성

---

## 6. 참고 문서

- [Infrastructure Rules](./infrastructure.md#L51) - 검증된 DB 구조
- [Data Schema](../data_schema.md) - 논리적 스키마 정의
- [Development Guide](./development.md) - Git Flow 및 배포 프로세스

---

**Review Status**: 🔴 Requires Immediate Action  
**Next Reviewer**: Architect Persona (스키마 설계 검토)

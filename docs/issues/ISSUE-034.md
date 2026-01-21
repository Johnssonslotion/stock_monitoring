# ISSUE-034: [Optimization] TimescaleDB Storage Efficiency (Compression & Retention)

## 1. 문제 정의 (Problem Definition)
Oracle Cloud Free Tier(Zero Cost) 환경에서 틱(Tick) 및 호가(Orderbook) 데이터를 TimescaleDB에 실시간으로 적재할 경우, 데이터 증가 속도에 비해 디스크 공간(100GB 중 여유 47GB)이 부족해질 위험이 있습니다. 특히 호가 데이터는 틱 보다 빈도가 높아 최적화가 필수적입니다.

## 2. 해결 방안 (Proposed Solution)
TimescaleDB의 고급 기능을 활용하여 스토리지 사용량을 최소화하고 가용성을 확보합니다.

1.  **Columnar Compression 활성화**: 
    *   `market_ticks` 및 `market_orderbook` 테이블에 압축 정책 적용.
    *   `symbol`과 `time`을 기준으로 세그먼트를 분할하여 90% 이상의 압축률 확보.
2.  **Retention Policy (보관 정책) 설정**:
    *   최근 7일치 데이터만 Hot Storage(TimescaleDB)에 유지.
    *   7일이 지난 데이터는 자동으로 Drop 처리하여 디스크 Full 장애 방지.
3.  **Chunk Time Interval 최적화**:
    *   메모리(24GB RAM) 효율을 위해 하이퍼테이블 청크 크기를 1시간 또는 6시간 단위로 조정.

## 3. 상세 세부 작업 (Tasks)
- [ ] `timescale_archiver.py` 내 `init_db`에 압축 활성화 DDL 추가
- [ ] 7일 보관 주기 자동화 스크립트/정책 적용
- [ ] 기존 적재 데이터 소급 압축 실행
- [ ] 디스크 사용량 모니터링 메트릭 강화

## 4. 기대 효과 (Expected Impact)
- 디스크 사용량 80% 이상 절감 (Zero Cost 유지)
- 오래된 데이터 자동 정리로 운영 부담 감소
- 압축된 데이터에 대한 쿼리 성능 향상 (IO 가용성 확보)

## 5. 의존성 (Dependencies)
- ISSUE-033: TimescaleArchiver Schema Mismatch (선결 조건 - 완료)

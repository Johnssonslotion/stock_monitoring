# IDEA: Volume Cross-Check Strategy (Anomaly Detection)
**Status**: 🌿 Sprouting → Referenced in [RFC-008 Appendix C/D](file:///home/ubuntu/workspace/stock_monitoring/docs/rfc/RFC-008-tick-completeness-qa.md)
**Priority**: P1

## 1. 개요 (Abstract)
틱 단위의 전수 검증(Tick-by-Tick Validation)은 정확하지만 API 호출 비용과 소요 시간이 과다하다. 이에 대한 효율적 대안으로, **거래량(Volume) 합계**를 비교하여 이상치(Anomaly)를 감지하는 **Volume Cross-Check Strategy**를 제안한다.

## 2. 문제 정의 (Problem)
- **Kiwoom/KIS 분봉 API 미지원**: `Trade Count` 필드가 없음.
- **Tick Counting 비용**: 1시간 검증 시 수십 회의 API 호출 필요 (O(N)).
- **목표**: 적은 비용(O(1))으로 신뢰할 수 있는 데이터 정합성 검증 수행.

## 3. 제안 전략 (Solution)
### Tier 1: Volume Delta Check (Volume Cross-Check)
- **Logic**: `API.MinuteVolume` vs `DB.SumTickVolume`
- **Threshold**: 오차율 **< 0.1%** (허용 오차)
- **API**:
    - Kiwoom: `ka10080` (분봉 차트) -> `trde_qty` (거래량)
    - KIS: `FHKST03010200` (분봉 조회) -> `cntg_vol` (체결량)
- **Process**:
    1. 검증 구간(예: 09:00~09:05)의 분봉 데이터 호출 (1회).
    2. 해당 구간의 거래량 합계 계산 (`API_VOL`).
    3. DB에서 동일 구간 틱 데이터의 거래량 합계 계산 (`DB_VOL`).
    4. `ABS(API_VOL - DB_VOL) / API_VOL` 계산.

### Tier 2: Tick Counting (Deep Verification)
- **Trigger**: Tier 1에서 오차율 > 0.1% 발생 시에만 수행.
- **Method**: Kiwoom `ka10079` (틱 차트)를 페이징하여 전수 카운팅.

## 4. 기대 효과
- **검증 속도 향상**: 5~10배 (틱 리스트 수집 불필요).
- **API 리소스 절약**: 호출 횟수 최소화.
- **실용성**: 거래량이 맞으면 틱 데이터도 맞을 확률이 매우 높음 (거래량은 체결의 결과이므로).

## 5. 로드맵 연동
- [ ] `scripts/quality/cross_validate_volume.py` 작성.
- [ ] `docs/data_management_strategy.md` 업데이트 (검증 섹션 추가).

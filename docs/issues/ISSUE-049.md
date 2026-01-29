# ISSUE-049: KIS TR ID Discovery & Validation (Pillar 8)

**Status**: In Progress
**Priority**: P0
**Type**: feature
**Created**: 2026-01-29
**Assignee**: Developer
**RFC**: RFC-010

## Problem Description

Pillar 8 (Market Intelligence) 구현을 위해 KIS API의 투자자 동향, 공매도, 프로그램 매매 관련 TR ID를 실제 API 호출을 통해 검증해야 합니다.

RFC-010에서 추정한 TR ID:
- 투자자동향: `FHPTJ04400000`, `FHKST01010900`, `FHPTJ04400100`
- 공매도: `FHPTJ04500000`, `FHPTJ04500100`
- 프로그램매매: `FHPTJ04300000`, `FHPTJ04300100`

## Acceptance Criteria

- [ ] KIS API Portal에서 정확한 TR ID 및 URL Path 확인
- [ ] Schema Discovery 테스트로 실제 응답 구조 수집
- [ ] `kis_tr_id_reference.md`에 Pillar 8 TR ID 추가
- [ ] 최소 3개 TR ID의 실제 API 호출 성공

## Technical Details

### 검증 대상 API 카테고리

1. **투자자별 매매동향**
   - 국내기관_외국인 매매종목가집계
   - 종목별 외국계 순매수추이
   - 투자자별 매매동향(종합)

2. **공매도 현황**
   - 국내주식 공매도 일별추이
   - 공매도 종합 정보 (잔고)

3. **프로그램 매매**
   - 종목별 프로그램매매추이
   - 프로그램매매 종합현황

### 검증 방법

```bash
# Schema Discovery 테스트 실행
PYTHONPATH=. poetry run pytest tests/integration/test_api_schema_discovery.py -v -s -m manual
```

## Resolution Plan

1. KIS Developers Portal에서 정확한 TR ID 확인
2. `kis_tr_id_reference.md` 업데이트
3. Schema Discovery 테스트 작성 및 실행
4. 응답 스키마 문서화

## Related

- Branch: `feature/pillar8-market-intelligence`
- RFC: [RFC-010](../governance/rfc/RFC-010-market-intelligence-pillar8.md)
- Blocks: ISSUE-050, ISSUE-051, ISSUE-052

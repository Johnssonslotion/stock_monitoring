# Kiwoom Tick Chart REST API Specification

**API Name**: 주식틱차트조회 (Stock Tick Chart Query)  
**TR Code**: `opt10079` (또는 유사 차트 TR)  
**Version**: v1  
**Protocol**: REST (POST) via Kiwoom REST Proxy  
**Status**: ✅ Planning  

---

## 1. Overview

사용자 피드백에 따르면, 이 API(틱 차트)는 개별 체결 내역(Raw Tick)을 리턴하는 것이 아니라, **특정 시간 단위(예: 1분, 60분 등) 내의 체결 틱 수(Tick Count)**를 확인할 수 있는 데이터를 제공합니다.

따라서 이 API는 **틱 누락 검증(Completeness Check)**의 핵심 "정답지(Ground Truth)"로 사용됩니다.
> "10:00~10:01 사이에 몇 틱이 발생했는가?" -> API: **150틱** vs DB: **148틱** -> **2틱 누락** 판정

---

## 2. Request

```json
{
  "tr_code": "opt10079",
  "inputs": {
    "종목코드": "005930",
    "틱범위": "1",  // 1틱 단위가 아니라 '틱 카운트 집계 범위'로 해석 가능성 있음
    "수정주가구분": "1"
  }
}
```

---

## 3. Response Interpretation (Verification Target)

응답 데이터의 **거래량(Volume)**이나 별도의 **틱 수(CNT)** 필드가 검증 대상입니다.

| Field | Description | Verification Logic |
|-------|-------------|--------------------|
| `체결시간` | YYYYMMDDHHMMSS | 검증 시간대 (Time Bucket) |
| `거래량` | 체결량 (Volume) | (보조) DB 수집 총 거래량과 비교 |
| `틱수` (추정) | **시간당 체결 횟수** | **(핵심) DB 수집 Row Count와 비교** |

> [!IMPORTANT]
> **검증 포인트**:
> 키움 API 응답에 명시적인 `Tick Count` 필드가 있거나, 혹은 `틱차트`의 특성상 Row 개수 자체가 틱 수를 의미하는지 확인하여,
> 실시간 수집된 DB의 `COUNT(*)`와 교차 검증합니다.

---

## 4. Verification Workflow

1. **Fetch**: 장 마감 후 `opt10079`로 주요 종목의 시간대별 틱 차트 데이터 수집.
2. **Aggregate**: DB(`market_ticks`)에서 동일 시간대(1분 등)로 `COUNT(*)` 집계.
3. **Compare**:
    - `API.TickCount` == `DB.RowCount` -> **Pass**
    - `API.TickCount` > `DB.RowCount` -> **Fail (Missing Data)** -> Gap Report 생성
4. **Alert**: 1% 이상 누락 시 관리자 알림.

---

## 5. Scheduling

```bash
# 매일 장 마감 후 (15:40) 검증 스크립트 실행
40 15 * * 1-5 python scripts/verify_tick_counts.py >> logs/tick_qa.log 2>&1
```

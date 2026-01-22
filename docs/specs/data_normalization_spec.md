# Spec: Data Normalization (API Standard Models)
**Status**: 🌿 Draft
**Category**: Data Architecture

## 1. 개요
다양한 브로커(KIS, Kiwoom, etc.)로부터 유입되는 이질적인 데이터를 시스템 내부에서 동일하게 처리하기 위한 표준 데이터 모델링 규격입니다.

## 2. 표준 데이터 모델 (Standard Models)

### 2.1. Normalized Tick (틱 데이터)
```python
{
    "time": "ISO8601",      # 예: 2026-01-21T09:30:00.123+09:00
    "symbol": "str",        # 정규화된 종목 코드 (예: "005930")
    "price": "float",       # 현재가
    "volume": "int",        # 체결량
    "change": "float",      # 전일 대비 등락
    "source": "enum",       # KIS, KIWOOM, BYPASS
    "raw": "dict"           # 원본 데이터 (필요 시 참조용)
}
```

### 2.2. Normalized Orderbook (호가 데이터)
- **Atomics**: 호가 레벨은 반드시 10단계 이상을 포함할 것.
- **Delta-first**: 동일한 호가 데이터는 전송하지 않으며, 변경된 부분만 전송(또는 전체 스냅샷).

## 3. 구현 원칙
- **Timestamp Priority**: 모든 데이터의 시간축은 한국 거래소(KST) 시간을 기준으로 정규화한다.
- **Precision**: 가격 데이터는 `Decimal` 또는 소수점 2자리(KRW), 4자리(USD) 정밀도를 유지한다.
- **Safety**: 정규화 실패 시 원본 데이터를 `data/error/`에 보존하고 Sentinel로 보고한다.

## 4. 로드맵
1. `src/core/models.py`에 Pydantic 기반 표준 모델 정의.
2. 각 Collector의 Parser를 모델 기반으로 리팩토링.
3. 데이터 아카이버(DuckDB/Timescale) 적용.

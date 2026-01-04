# 실험 전략 및 격리 프로토콜 (Experimentation Spec)

**작성일**: 2026-01-04
**담당자**: PM, Architect, Data Scientist

## 1. 개요
"Fail Fast, Fail Safe".
검증되지 않은 전략이 운영 환경(Production)을 오염시키는 것을 방지하고, 자유로운 가설 검증을 지원하기 위한 격리 및 통합 프로세스를 정의한다.

## 2. 실험 생명주기 (Lifecycle)
1.  **가설 수립 (Idea)**: "이평선 20일과 60일 골든크로스에 매수하면 수익이 날까?"
2.  **백테스팅 (Backtest)**: 과거 데이터(Cold Data, DuckDB/Parquet)를 사용하여 가설 검증.
3.  **모의 투자 (Paper Trading)**:
    -   실시간 데이터(Hot Data, Redis)를 사용하되, 주문은 가상으로 체결.
    -   최소 1주 이상 가동하며 MDD 및 수익률 검증.
4.  **운영 반영 (Live Trading)**: 검증된 전략을 운영 환경으로 승격(Promotion).

## 3. 격리 전략 (Isolation Strategy)
### 3.1 코드 격리 (Branch Strategy)
-   **실험용 (`exp/`)**:
    -   자유로운 실험 공간. 커밋 컨벤션이 다소 느슨해도 허용.
    -   절대 `master`로 직접 Merge 하지 않는다.
-   **운영용 (`feat/` -> `master`)**:
    -   실험이 성공하면, 운영용 품질(DoD 준수)에 맞춰 코드를 **새로 작성(Refactor)**하거나 정제하여 `feat/` 브랜치 생성.
    -   Strict Code Review 후 Merge.

### 3.2 데이터/인프라 격리
-   **Compute**: 실험용 워커(`worker-exp`)는 Docker Resource Limit(CPU 0.5, RAM 1GB)을 설정하여 운영 워커(`worker-prod`)의 자원을 침범하지 않는다.
-   **Data**:
    -   운영 DB(Redis Main Index, DuckDB)는 **Read-Only** 권한으로만 접근.
    -   실험 결과 및 로그는 별도 공간(`data/exp/`, Redis Index 10+)에 저장.

## 4. 파라미터 통합 관리 (Configuration Management)
하드코딩을 방지하고 빠른 튜닝을 지원하기 위해 **Config Registry** 패턴을 도입한다.

### 4.1 구조
-   모든 전략 설정은 `configs/` 디렉토리에 YAML/JSON으로 관리.
-   Python 코드(`src/core/config.py`)에서 `Pydantic`을 사용하여 유효성 검증(Validation) 및 로드.

### 4.2 예시
```yaml
# configs/strategy_v1.yaml
strategy_name: "golden_cross"
parameters:
  short_window: 20
  long_window: 60
  stop_loss_pct: 0.02
```

```python
# src/strategy/base.py
class StrategyConfig(BaseModel):
    short_window: int = Field(gt=0)
    long_window: int = Field(gt=0)
    # 코드는 변경 없이 YAML 파일만 교체하여 다른 실험 수행 가능
```

## 5. 승격 기준 (Promotion Criteria)
다음 조건을 만족해야 운영 반영(Live Trading) 승인을 요청할 수 있다.
1.  **수익률**: 벤치마크(KOSPI/BTC) 대비 초과 수익 달성.
2.  **안정성**: MDD 5% 미만 (Paper Trading 기간 중).
3.  **코드 품질**: AI Rules의 DoD(테스트, 린트, 문서화) 100% 준수.

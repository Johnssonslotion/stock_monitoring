# 차트 기능 고도화 전략 (Advanced Chart Strategy)

이 문서는 Antigravity 프로젝트의 시각화 엔진을 상용 트레이딩 터미널 수준으로 끌어올리기 위한 단계별 고도화 전략을 담고 있습니다.

## 1. 핵심 목표 (Core Objectives)
- **정보 밀도 극대화**: 단순 가격 나열을 넘어, 기술적 지표와 재료(News)를 통합하여 의사결정 속도 향상.
- **반응성 최적화**: 수백만 개의 틱 데이터 중 필요한 구간을 지연 없이 렌더링.
- **분석 자동화**: 시각적 패턴 및 이상 징후 자동 탐지 레이어 추가.

## 2. 주요 제안 기능 (Proposed Features)

### A. 기술적 지표 패키지 (Advanced Indicators)
- **모멘텀 지표**: RSI, MACD, Stochastic.
- **변동성 지표**: Bollinger Bands, ATR.
- **추세 지표**: 다중 이평선(EMA, SMA), Ichimoku Cloud.

### B. 뉴스 및 이벤트 오버레이 (Event Overlay)
- **타임라인 매핑**: 차트 시간축 위에 중요 뉴스 아이콘 표시. 클릭 시 요약 정보 팝업.
- **시그널 표시**: 특정 알고리즘(예: Golden Cross) 발생 지점에 화살표 및 라벨링.

### C. 멀티-타임프레임 동기화 (Multi-Sync)
- **비교 분석**: 두 개 이상의 종목(예: 삼성전자 vs TSMC) 또는 지수-종목 간 상관관계 시각화.
- **크로스 헤어 동기화**: 한 차트에서 커서를 움직이면 다른 시간대 차트에서도 동일 시점을 포인팅.

### D. 실시간 스트리밍 아키텍처 (Streaming)
- **WebSocket 연동**: Polling 방식에서 Push 방식으로 전환하여 1초 미만의 갱신 지연 실현.

---

## 3. 6인의 페르소나 검토 보고서 (Persona Review)

### 👔 Project Manager (PM)
> "고도화의 핵심은 '예쁜 차트'가 아니라 **'돈을 벌어주는 차트'**여야 합니다. 너무 많은 지표는 오히려 노이즈가 될 수 있으므로, 사용자가 커스텀하여 본인만의 레이아웃을 저장할 수 있는 기능을 우선순위에 둡시다. 납기는 핵심 지표 3종(RSI, MACD, BB) 우선 구현으로 설정합니다."

### 🏛️ Architect
> "기술 지표 계산 로직을 Dashboard 모듈에서 분리하여 `src/analysis/indicators.py`와 같이 독립된 패키지로 구축해야 합니다. 또한, 실시간 스트리밍 도입 시 API 서버와의 결합도를 낮추기 위해 Pub/Sub 메시지 규격을 엄격히 정의해야 합니다."

### 🔬 Data Scientist
> "지표 계산 시 매번 전체 데이터를 읽는 것은 비효율적입니다. TimescaleDB의 **Continuous Aggregates**를 지표 계산용으로 확장하거나, 윈도우 함수를 활용한 증분 계산(Incremental Calculation) 방식을 적용하여 고성능을 유지해야 합니다. 지표 데이터 역시 Cold Data로 전환 시 Parquet으로 압축 저장할 준비를 하세요."

### 🔧 Infrastructure Engineer
> "WebSocket 스트리밍은 많은 동시 접속 발생 시 서버 메모리를 점유합니다. 오라클 프리티어 리소스(24GB RAM)를 초과하지 않도록 커넥션 풀링과 메시지 압축(JSON -> Protobuf 고려) 전략이 필요합니다. 렌더링 부하를 클라이언트(Browser)로 분산시키되, 브라우저가 죽지 않도록 데이터 포인트 제한(Downsampling)을 적용해야 합니다."

### 👨‍💻 Developer
> "Plotly Subplots 구조를 컴포넌트화하여 새로운 지표가 추가되더라도 코드 수정이 최소화되도록 설계하겠습니다. DoD(Definition of Done)에 따라 각 지표의 수식 검증을 위한 단위 테스트를 선행하겠습니다."

### 📝 Doc Specialist
> "추가되는 모든 기술적 지표에 대해 한글로 된 계산 로직 및 활용법 주석을 강제하겠습니다. 특히 RSI나 MACD의 파라미터(12, 26, 9 등)가 무엇을 의미하는지 독스트링에 명확히 기재하여 운영자가 이해할 수 있게 하겠습니다."

### 🧪 QA Engineer
> "틱 데이터 유실 상황이나 API 장애 시 차트가 깨지지 않고 마지막 상태를 유지하는지(Graceful Degradation) 검증하겠습니다. 또한 극단적인 변동성(급등락) 상황에서 지표 계산이 오버플로우 없이 정상 작동하는지 카오스 테스트를 수행할 예정입니다."

---

## 4. 향후 로드맵 (Roadmap)
1. **Short-term**: 주요 지표 3종 추가 및 Continuous Aggregate 최적화.
2. **Mid-term**: 뉴스 오버레이 및 WebSocket 스트리밍 전환.
3. **Long-term**: AI 기반 패턴 인식 레이어 및 알림 엔진 통합.

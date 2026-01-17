# Base Strategy Specification

## 1. 개요 (Overview)
`Strategy` 클래스는 모든 백테스팅 및 라이브 트레이딩 전략의 모체(Parent Class)가 되는 추상 클래스(ABC)입니다. 이 명세는 전략 구현체가 반드시 준수해야 할 인터페이스와 데이터 구조를 정의합니다.

## 2. 데이터 구조 (Data Structures)

### 2.1 Enums
- **OrderSide**: `BUY`("buy"), `SELL`("sell")
- **OrderType**: `MARKET`("market"), `LIMIT`("limit")

### 2.2 Signal
전략이 생성하는 매매 신호의 표준 규격입니다.
```python
@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    reason: str = ""
```

### 2.3 Position
현재 보유 중인 포지션 상태를 나타냅니다.
- **Properties**:
    - `market_value`: 현재 평가금액 (`quantity * current_price`)
    - `unrealized_pnl`: 미실현 손익 (`(current - avg) * qty`)

## 3. 인터페이스 (Interfaces)

### 3.1 필수 구현 (`@abstractmethod`)
하위 클래스는 다음 메서드를 반드시 구현해야 합니다.

#### `async def on_tick(self, tick_data: dict)`
- **Trigger**: 실시간 틱 수신 시 호출.
- **Input Schema**:
    ```python
    {
        'timestamp': datetime,
        'symbol': str,
        'price': float,
        'volume': int,
        'market': str  # 'KR' or 'US'
    }
    ```
- **Responsibility**: 내부 상태(Price History, Technical Indicator 등) 업데이트.

#### `def generate_signals(self) -> List[Signal]`
- **Trigger**: 틱 처리 후 또는 주기적으로 호출.
- **Output**: 실행할 매매 신호 리스트. 신호가 없으면 빈 리스트 반환.

### 3.2 선택적 구현 (`Optional`)
- `on_order_filled(signal, fill_price)`: 체결 확인 시 포트폴리오 동기화 로직.

## 4. 제약 사항 (Constraints)
1.  **State Isolation**: 각 전략 인스턴스는 독립적인 `positions`와 `cash` 상태를 가진다.
2.  **No Side Effects**: `generate_signals`는 순수 함수에 가깝게 동작해야 하며, 외부 시스템(DB 등)에 직접 쓰기 작업을 수행해서는 안 된다.

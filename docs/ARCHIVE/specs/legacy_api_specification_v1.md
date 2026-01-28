# OpenAPI Specification (v1.0)

본 문서는 `Immutable Law #7 (Schema Strictness)`에 의거하여 작성된 **Machine-Readable API Specification**입니다.
서버와 클라이언트는 본 명세를 기준(Contract)으로 구현되어야 합니다.

## Specification (YAML)
```yaml
openapi: 3.1.0
info:
  title: Antigravity Stock API
  version: 1.0.0
  description: |
    Stock Monitoring System을 위한 REST API 및 WebSocket 명세.
    Dual Socket 아키텍처 및 Frontend Backlog 요구사항을 포괄함.

servers:
  - url: http://localhost:8000
    description: Local Development
  - url: http://{host}:8000
    description: Production (Tailscale VPN)

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-KEY
    # [Backlog] OAuth2/JWT Integration
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    # --- Primitive Types ---
    Timestamp:
      type: string
      format: date-time
      example: "2026-01-17T09:30:00+09:00"
    
    Symbol:
      type: string
      pattern: "^[A-Z0-9]+$"
      example: "005930"

    # --- Domain Models ---
    Tick:
      type: object
      required: [time, symbol, price, volume, source]
      properties:
        time:
          $ref: '#/components/schemas/Timestamp'
        symbol:
          $ref: '#/components/schemas/Symbol'
        price:
          type: number
          format: double
        volume:
          type: number
          format: double
        change:
          type: number
          format: double
        source:
          type: string
          enum: [KIS, KIWOOM, BYPASS]

    Orderbook:
      type: object
      required: [time, symbol, total_ask_qty, total_bid_qty, asks, bids]
      properties:
        time:
          $ref: '#/components/schemas/Timestamp'
        symbol:
          $ref: '#/components/schemas/Symbol'
        total_ask_qty:
          type: number
        total_bid_qty:
          type: number
        asks:
          type: array
          items:
            $ref: '#/components/schemas/OrderbookLevel'
        bids:
          type: array
          items:
            $ref: '#/components/schemas/OrderbookLevel'

    OrderbookLevel:
      type: object
      required: [price, volume]
      properties:
        price:
          type: number
        volume:
          type: number

    Candle:
      type: object
      required: [time, open, high, low, close, volume]
      properties:
        time:
          $ref: '#/components/schemas/Timestamp'
        open:
          type: number
        high:
          type: number
        low:
          type: number
        close:
          type: number
        volume:
          type: number

    # --- Response Wrappers ---
    MarketMapItem:
      type: object
      properties:
        symbol: 
          $ref: '#/components/schemas/Symbol'
        name:
          type: string
        marketCap:
          type: number
        price:
          type: number
        change:
          type: number
        category:
          type: string

    HealthStatus:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        timestamp:
          $ref: '#/components/schemas/Timestamp'
        db:
          type: object
        redis:
          type: object

paths:
  # --- Market Data (Existing) ---
  /api/v1/ticks/{symbol}:
    get:
      summary: 최근 틱 데이터 조회
      security:
        - ApiKeyAuth: []
      parameters:
        - name: symbol
          in: path
          required: true
          schema:
            $ref: '#/components/schemas/Symbol'
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
      responses:
        '200':
          description: List of Ticks
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Tick'

  /api/v1/orderbook/{symbol}:
    get:
      summary: 최신 호가 조회
      security:
        - ApiKeyAuth: []
      parameters:
        - name: symbol
          in: path
          required: true
          schema:
            $ref: '#/components/schemas/Symbol'
      responses:
        '200':
          description: Snapshot of Orderbook
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Orderbook'

  /api/v1/candles/{symbol}:
    get:
      summary: 캔들(OHLCV) 조회
      parameters:
        - name: symbol
          in: path
          required: true
          schema:
            $ref: '#/components/schemas/Symbol'
        - name: interval
          in: query
          schema:
            type: string
            enum: [1m, 5m, 15m, 1h, 1d]
            default: 1d
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Candle'

  /api/v1/market-map/{market}:
    get:
      summary: 시장 지도(Treemap) 데이터
      parameters:
        - name: market
          in: path
          schema:
            type: string
            default: us
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  symbols:
                    type: array
                    items:
                      $ref: '#/components/schemas/MarketMapItem'

  # --- System ---
  /api/v1/health:
    get:
      summary: 시스템 상태 확인 (Heartbeat)
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthStatus'

  # --- BACKLOG ITEMS (Frontend Requests) ---
  
  # [Req-FE-001] User Layout Settings Persistence
  /api/v1/user/settings:
    get:
      summary: [Backlog] 사용자 UI 설정 조회
      tags: [Frontend, Backlog]
      security:
        - ApiKeyAuth: []
      responses:
        '200':
          description: User layout configuration
          content:
            application/json:
              schema:
                type: object
                properties:
                  theme:
                    type: string
                    enum: [dark, light]
                  layout_json:
                    type: string
                    description: "Gridstack.js serialized layout"
    post:
      summary: [Backlog] 사용자 UI 설정 저장
      tags: [Frontend, Backlog]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [layout_json]
              properties:
                theme:
                  type: string
                layout_json:
                  type: string
      responses:
        '200':
          description: Saved successfully

  # [Req-FE-002] Multi-Chart Sync Configuration
  /api/v1/config/charts:
    get:
      summary: [Backlog] 멀티 차트 동기화 설정
      tags: [Frontend, Backlog]
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    group_id:
                      type: string
                    symbols:
                      type: array
                      items:
                        $ref: '#/components/schemas/Symbol'

  # [Req-FE-003] Authentication (OAuth2/JWT)
  /api/v1/auth/token:
    post:
      summary: [Backlog] Access Token 발급
      tags: [Auth, Backlog]
      requestBody:
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                username:
                  type: string
                password:
                  type: string
      responses:
        '200':
          description: Returns JWT Token
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  token_type:
                    type: string
```

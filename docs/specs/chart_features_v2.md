# 📊 Chart Visualization V2 Specification (The Golden Consensus)

**Version**: 2.0  
**Based on**: [Innovation Council Report](../reports/20260117_chart_innovation_council.md)  
**Status**: Ready for Implementation  
**Component**: `CandleChart.tsx`

---

## 1. Overview
10번의 "Innovation Loop"를 통해 도출된 **Golden Consensus**를 기반으로, 데이터 무결성(DS), 트레이딩 적합성(Quant), 몰입형 경험(UX)을 모두 만족하는 차트 V2 스펙을 정의합니다.

## 2. Quantitative Indicators (지표 고도화)

### 2.1 VWAP (Volume Weighted Average Price)
-   **Definition**: 거래량으로 가중 평균한 가격. 기관 투자자의 벤치마크.
-   **Formula**: `Cumulative(Price * Volume) / Cumulative(Volume)` (장 시작 시점부터 누적)
-   **Visual Spec**:
    -   **Style**: Solid Line
    -   **Color**: `#A855F7` (Purple-500)
    -   **Width**: `2px` (Hierarchy: High)
    -   **Effect**: `drop-shadow(0 0 2px #A855F7)` (Neon Glow)

### 2.2 Bollinger Bands (Volatility Context)
-   **Definition**: 이동평균선(MA20)을 중심으로 표준편차(σ) 범위를 표시.
-   **Formula**:
    -   Mid: `SMA(20)`
    -   Upper: `Mid + (2 * StdDev)`
    -   Lower: `Mid - (2 * StdDev)`
-   **Visual Spec**:
    -   **Style**: Area Fill (No Stroke)
    -   **Color**: `rgba(59, 130, 246, 0.05)` (Blue with 5% Opacity)
    -   **Context**: 캔들 뒤(Back)에 배치하여 배경처럼 인식되게 함.

### 2.3 Volume Moving Average
-   **Definition**: 거래량의 추세 확인.
-   **Visual Spec**:
    -   **Style**: Line Overlay on Histogram
    -   **Color**: `#9CA3AF` (Gray-400), Opacity 0.8
    -   **Width**: `1px`

## 3. UX & Interaction (사용자 경험)

### 3.1 Smart Floating Legend
-   **Problem**: 좌상단 고정 범례가 최근 데이터를 가림.
-   **Solution**: **Backdrop Blur** & **Smart Position**
-   **Spec**:
    -   **Background**: `bg-black/20 backdrop-blur-[2px]`
    -   **Border**: `border border-white/5`
    -   **Content**: `O H L C Vol` + `Indicator Values (VWAP, BB)`

### 3.2 Magnet Crosshair
-   **Spec**: **X-Axis Snap ONLY**
    -   **X (Time)**: 마우스가 캔들 영역 어디에 있든, 가장 가까운 시간축(Time Grid)에 자석처럼 붙음(Snap).
    -   **Y (Price)**: 사용자가 자유롭게 이동 가능(Free). (가격을 읽는 자유도 보장)
    -   **Style**: `Dashed Line`, `Opacity 0.4`

### 3.3 Dynamic Viewport (Revisited)
-   **Market Active**: 15:30까지 공백 확보 (Gap).
-   **Market Closed**: 우측 정렬 (Align Right).
-   **Initial Zoom**: 최근 120개 캔들만 Load (Focus).

## 4. Visual References (기준선)
-   **Prev Close Line**: 전일 종가. Horizontal, Dotted, Gray-500.
-   **Market Close Line**: 15:30 시점. Vertical, Dashed, Gray-700.

---

## 5. Technical Implementation Plan
1.  **Utils**: `src/utils/tradingIndicators.ts` 생성 (VWAP, SMA, StdDev 계산 함수).
2.  **Series**: `CandleChart.tsx`에 `addLineSeries` (VWAP), `addAreaSeries` (Bollinger in progress - or simple lines filled) 추가.
    *   *Note: Lightweight Charts의 Area Series는 0부터 채워지므로, 밴드 표현을 위해선 `createMultipleAttributes`나 Custom Series가 필요할 수 있으나, V2 초기엔 Upper/Lower Line으로 대체 가능.* -> **Decision**: Upper/Lower Line + Cloud Color (if supported) or just Lines for V1.5. (Refined: Use Cloud logic if using plugins, else simple lines).
3.  **State**: `hoveredCandle` 상태를 `FloatingLegend` 컴포넌트로 분리 최적화.

---

## 6. Appendix
-   [Full Transcript of Council Meeting](../reports/20260117_chart_innovation_council.md)

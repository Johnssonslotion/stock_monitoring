# 🎨 UX Re-examination & Cross-Verification Report

**Date**: 2026-01-17
**Target**: `CandleChart.tsx` (1-Minute Visualization)
**Focus**: UX Limitations & Professional Usability

---

## 1. Current Limitations (UX Audit)

현재 구현된 차트 시각화 코드를 정밀 분석한 결과, 다음과 같은 **치명적 UX 한계(Critical UX Gaps)**가 발견되었습니다.

### 🔴 1.1 Lack of Information (정보 부족)
-   **No Floating Tooltip**: 마우스를 캔들 위에 올렸을 때 **시가/고가/저가/종가(OHLC)** 및 거래량의 정확한 수치를 확인할 수 없습니다. (현재: Crosshair만 나오고 수치는 축에만 표시됨)
-   **No Active Legend**: 차트 좌상단에 종목명과 현재가만 있을 뿐, `Open: 100, High: 110...` 과 같은 동적 범례(Legend)가 없습니다.

### 🔴 1.2 Visual Noise (시각적 노이즈)
-   **Grid Lines**: 기본 격자선이 너무 강해(Color opacity issue) 캔들 흐름을 방해할 가능성이 있습니다.
-   **Volume Overlap**: 거래량 히스토그램이 가격 캔들과 겹칠 때(Overlay), 반투명 처리는 되었으나 구분이 모호하여 가독성을 해칩니다.

### 🔴 1.3 Missing Standards (표준 부재)
-   **Moving Averages (이평선) 부재**: 트레이더의 기본 도구인 **5일/20일 이동평균선**이 없어 추세 파악이 어렵습니다. (현재: Mock VWAP만 존재)
-   **Time Scale Format**: 1분봉임에도 X축 시간 포맷이 명확하지 않을 수 있습니다.

---

## 2. Persona Cross-Verification (교차 검증)

### 👔 PM (Product Manager)
> **"Not Professional Yet."**
> "현재는 단순히 데이터를 그림으로 보여주는 수준입니다. 사용자가 '분석'을 하려면 마우스를 움직일 때마다 가격 정보가 즉각적으로 피드백(Tooltip)되어야 합니다. 경쟁사(TradingView 등) 대비 디테일이 부족합니다."

### 🏛️ Architect
> **"Performance Concern."**
> "Tooltip을 구현할 때 React State를 너무 빈번하게 업데이트하면 렌더링 성능이 저하될 수 있습니다. `subscribeCrosshairMove` 이벤트를 최적화하여 DOM 직접 조작(Direct DOM Manipulation) 방식을 권장합니다."

### 🔬 Data Scientist
> **"Indicator Value."**
> "1분봉에서 단순 캔들만 보는 것은 의미가 약합니다. **MA5, MA20** 라인을 추가하여 '골든크로스' 같은 시각적 신호를 제공해야 UX가 완성됩니다."

### 🎨 Frontend Lead (New Persona Opinion)
> **"Visual Hierarchy."**
> "배경색, 그리드, 캔들 색상의 대비(Contrast)를 재조정해야 합니다. 현재 거래량이 캔들을 가리는 문제는 히스토그램 높이를 제한하거나(`scaleMargins`), 별도 패널로 분리하는 것이 정석입니다."

---

## 3. Improvement Plan (개선안)

### ✅ Action 1: Floating Legend (동적 범례) 구현
-   **위치**: 차트 좌상단 (절대 위치)
-   **내용**: `O: 10,200 H: 10,300 L: 10,100 C: 10,250 Vol: 520` (Hover 시 실시간 업데이트)
-   **UX 효과**: 마우스 이동만으로 정확한 데이터 스캐닝 가능.

### ✅ Action 2: Moving Averages (이동평균선) 추가
-   **항목**: MA5(Blue), MA20(Yellow), MA60(Green)
-   **구현**: `addLineSeries` 활용.
-   **UX 효과**: 추세 및 지지/저항 라인 시각화.

### ✅ Action 3: Visual Polish
-   **Volume**: 높이를 15%로 축소하여 캔들과 겹침 최소화.
-   **Crosshair**: 점선 스타일(Dotted) 및 자석 모드(Magnet) 활성화.

---

## 4. Conclusion
단순 뷰포트 조정을 넘어, **"Interactive Information Layer"**를 추가해야만 UX가 완성됩니다. 
즉시 **Floating Legend**와 **이평선(MA)** 추가 작업을 제안합니다.

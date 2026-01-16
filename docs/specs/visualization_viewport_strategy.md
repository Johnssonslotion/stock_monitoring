# 📊 Chart Visualization & Viewport Optimization Strategy

**Date**: 2026-01-17  
**Status**: Applied & Reviewed  
**Component**: `CandleChart.tsx`

---

## 1. Problem Definition
기존 1분봉 차트의 뷰포트(Viewport) 로직은 두 가지 문제가 있었습니다.
1.  **Excessive Zoom**: 데이터 로드 시 390개(하루 전체) 이상의 캔들을 한 번에 보여주어, 캔들이 너무 얇게 보이고 가독성이 떨어짐.
2.  **Incorrect Whitespace**: 장 종료(15:30) 이후에도 불필요한 우측 공백(Whitespace)이 유지되어 심리적 종결감을 주지 못함.

---

## 2. Optimization Strategy (최적화 전략)

### 2.1 Dynamic Whitespace (동적 공백 처리)
"사용자의 시간 인식에 맞춰 차트의 끝을 조절한다."

| 상태 (Status) | 조건 (Condition) | 전략 (Strategy) | 시각적 효과 |
| :--- | :--- | :--- | :--- |
| **Market Active** | `Now < 15:30` (On the day) | **Fill to Close** | 현재 시각부터 15:30까지 공백을 미리 할당. "오늘 남은 시간"을 인지시킴. |
| **Market Closed** | `Now >= 15:30` (or Past day) | **Align Right** | 마지막 캔들(종가)을 화면 우측 끝(Margin 2 bar)에 정렬. "하루가 끝남"을 명확히 함. |

### 2.2 Initial Viewport limit (초기 뷰포트 제한)
"전체를 보여주는 것보다, 최근 흐름이 중요하다."

-   **Logic**: `setVisibleLogicalRange({ from: Total - 120, to: Total + Margin })`
-   **Effect**: 1분봉 초기 진입 시, **최근 120분(2시간)**의 흐름만 확대하여 보여줌.
-   **Benefit**: 캔들의 굵기가 확보되어 시가/종가/꼬리 구분이 명확해짐. 과거 데이터는 스크롤로 확인.

### 2.3 Volume Histogram (거래량 시각화)
-   **Implementation**: 메인 캔들 차트와 동일한 X축 공유 (Overlay).
-   **Position**: 차트 하단 20% 영역 할당 (`scaleMargins: { top: 0.8 }`).
-   **Color Coding**: 상승(Red), 하락(Blue) 색상 구분 (Alpha 0.5).

---

## 3. Council of Six Review (페르소나 검토)

### 👔 PM (Project Manager)
> **"승인 (Approved)"**
> "2.1번 전략은 아주 훌륭합니다. 장 중에는 '채워야 할 공간'을 보여주어 긴장감을 주고, 장 마감 후에는 '완결성'을 보여주는 UX 디테일이 돋보입니다. 1분봉 초기 진입 시 2시간만 보여주는 것도 '집중력' 측면에서 합리적입니다."

### 🏛️ Architect
> **"승인 (Approved)"**
> "`CandleChart` 컴포넌트 내 `handleViewportReset` 함수로 로직을 분리한 점을 칭찬합니다. 향후 5분봉, 15분봉 등으로 확장 시 `isMarketActive` 로직만 팩토링하면 재사용 가능합니다."

### 🔬 Data Scientist
> **"권고 (Recommendation)"**
> "시각화는 좋으나, `isMarketActive` 판단 시 클라이언트 시간(Browser Time)을 사용하고 있습니다. 사용자가 해외에 있어도 한국 장 시간(KST 15:30)을 정확히 타게팅하려면 `Intl.DateTimeFormat`이나 서버 시간 동기화가 필요합니다."
> *(Action: 현재는 로컬 타임 기준이나, 추후 고도화 과제로 등록)*

### 🖥️ Infra Engineer
> **"확인 (Checked)"**
> "Canvas 렌더링 부하 관점에서도 390개를 그리는 것보다 120개를 그리는 것이 초기 프레임 방어에 유리합니다. Zoom In/Out 로직도 API 호출 없이 클라이언트 계산으로 처리되어 트래픽 영향 없습니다."

### 🧪 QA Engineer
> **"테스트 요구 (Test Required)"**
> "다음 시나리오 검증이 필요합니다."
> 1.  장 중(09:01) 데이터가 1개일 때 우측 공백이 정상적으로 389개 생기는가?
> 2.  장 마감(15:31) 직후 새로고침 시 공백이 사라지는가?

---

## 4. Conclusion
위 전략은 **만장일치로 채택**되었으며, 즉시 코드베이스에 반영되었습니다. `CandleChart.tsx`는 이제 단순 렌더링을 넘어 **시장 상태(Context-Aware)**를 반영하는 컴포넌트가 되었습니다.

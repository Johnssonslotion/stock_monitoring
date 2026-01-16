# 🧠 Chart Innovation Council: 10 Iteration Loops

**Date**: 2026-01-17
**Participants**:
- **🔬 Data Scientist (DS)**: "데이터의 무결성과 통계적 유의미함이 최우선."
- **⚡ Quant Trader (QT)**: "체결 속도와 집행 기준(Benchmark)이 중요."
- **🎨 UX Designer (UX)**: "인지 부하(Cognitive Load)를 최소화하고 몰입감을 제공."

**Rule**: No Summary. Full Dialogue Records.

---

## 🔄 Loop 1: 기본 정보의 위치 (The Anchor)

**UX**: "현재 Floating Legend가 좌상단에 고정되어 있는데, 차트를 확대하면 과거 캔들을 가려버립니다. 최악의 경험이에요."

**QT**: "동의합니다. 하지만 시선은 왼쪽 위에서 시작하므로(F-Pattern), 거기에 정보가 없으면 불안합니다."

**DS**: "정보를 숨길 순 없습니다. OHLCV는 항상 보여야 합니다. 데이터 포인트가 가려지는 건 캔들의 중요도에 따라 다릅니다. 최근 캔들이 가장 중요하죠."

**✅ Decision**: "Legend를 좌상단에 유지하되, **배경을 반투명 블러(Backdrop Blur)** 처리하고, 캔들과 겹침이 감지되면 자동으로 우측으로 피하거나(Smart Positioning) 상단 별도 헤더바(Header Bar)로 분리한다."

---

## 🔄 Loop 2: 지표의 선택 - MA vs VWAP

**QT**: "지금 MA5, MA20을 넣었다고 좋아하던데, 그건 '후행 지표(Lagging)'입니다. 우리 같은 퀀트 팀은 **VWAP(거래량 가중 평균 가격)**이 없으면 차트를 안 봅니다. 기관의 집행 벤치마크니까요."

**DS**: "맞습니다. 1분봉 같이 노이즈가 심한(High Variance) 데이터에서 단순 이동평균(SMA)은 휩소(Whipsaw) 신호를 너무 많이 줍니다. VWAP를 메인 추세선으로 승격시켜야 합니다."

**UX**: "그럼 선이 3개가 되나요? (MA5, MA20, VWAP). 너무 복잡합니다. 색상 코딩은 어떻게 하죠?"

**✅ Decision**: "MA5/20은 얇은 선(1px)으로 유지하되, **VWAP는 굵은 선(2px) 또는 네온 효과**를 주어 위계(Hierarchy)를 구분한다. 당일 VWAP(Anchored VWAP)를 기본으로 채택한다."

---

## 🔄 Loop 3: 변동성 시각화 (Volatility)

**DS**: "가격만 보여주면 '이 가격이 싼지 비싼지' 모릅니다. **Bollinger Bands(볼린저 밴드)**의 표준편차(Sigma) 영역을 배경에 은은하게 깔아줘야 합니다. 그래야 이상치(Outlier)를 직관적으로 알 수 있죠."

**UX**: "또 선을 추가한다고요? 차트가 스파게티가 됩니다. 선 대신 **영역 채우기(Area Fill)**를 제안합니다. 상단/하단 밴드 사이를 아주 옅은 파란색(Alpha 0.05)으로 채우면 시각적 노이즈 없이 정보 전달이 가능합니다."

**QT**: "좋습니다. 밴드 폭이 좁아지면(Squeeze) 곧 변동성이 터진다는 신호니까 시각적으로도 훌륭하겠네요."

**✅ Decision**: "볼린저 밴드 추가. 단, 외곽선은 제거하고 **내부 영역만 투명도 5%로 렌더링**하여 배경처럼 느끼게 한다."

---

## 🔄 Loop 4: 거래량의 의미 (Volume Logic)

**QT**: "지금 거래량 색상이 캔들 색상을 따라가는데(양봉이면 빨강, 음봉이면 파랑), 이건 반쪽짜리 정보입니다. 주가가 올라도 매도세가 강할 수 있습니다(매도벽 체결). 하지만 틱 데이터가 없으니 지금은 어쩔 수 없군요."

**DS**: "대신 **Volume MA (거래량 이평선)**을 추가합시다. 거래량이 평소보다 2배 터졌는지 시각적으로 바로 알 수 있어야 합니다. 'Volume Spikes'는 중요한 모델 피처니까요."

**UX**: "거래량 바 위에 얇은 회색 선으로 20일 거래량 평균을 얹읍시다. 임계치를 넘는 바(Bar)는 채도를 높여서 강조합시다."

**✅ Decision**: "Volume Histogram 위에 **Volume MA(20)** 라인 오버레이 추가."

---

## 🔄 Loop 5: 시간축 인식 (Time Perception)

**UX**: "현재 1분봉에서 15:30 이후 빈 공간을 보여주는 건 좋은데, 그 경계선(Market Close Line)이 명확하지 않습니다. 세로 점선(Vertical Dashed Line)을 그어 '여기서 장 마감'임을 명시해야 합니다."

**DS**: "그리고 전일 종가(Yesterday Close) 라인도 필요합니다. 갭 상승/하락을 바로 인지할 수 있게요."

**QT**: "전일 종가는 심리적 지지선입니다. 차트 전체를 가로지르는 **가로 점선(Horizontal Line)**이 필요합니다. 라벨은 'Prev Close'로 하죠."

**✅ Decision**: "장 마감 세로선(Vertical) 및 전일 종가 가로선(Horizontal) 추가."

---

## 🔄 Loop 6: 상호작용 감도 (Interactive Sensitivity)

**QT**: "마우스 십자선(Crosshair)이 캔들 중간에 어정쩡하게 걸치는 게 싫습니다. **'Magnet Mode'**를 강제해서 항상 O/H/L/C 값 중 가까운 곳이나 Time Grid에 딱딱 붙게 해주세요."

**UX**: "너무 강한 자석은 자유도를 해칩니다. 캔들의 수직 중심선(Time)에는 붙되, 가격(Price)은 자유롭게 움직이는 'Semi-Magnet'이 좋습니다. 그래야 캔들 사이의 갭(Gap)도 측정하죠."

**DS**: "동의합니다. X축(시간)은 Discrete하지만, Y축(가격)은 Continuous합니다. X축만 스냅(Snap)을 적용합시다."

**✅ Decision**: "Crosshair Behavior: **X축 Snap-to-Candle, Y축 Free**."

---

## 🔄 Loop 7: 색의 심리학 (Color Psychology)

**UX**: "현재 배경이 완전 투명(Transparent)인데, 데이터 밀도가 높아지면 가독성이 떨어집니다. 차트 영역만이라도 아주 짙은 남색(Deep Navy) 배경을 깔아야 색상 대비(Contrast)가 살아납니다."

**DS**: "그리드 라인도 `rgba(255,255,255, 0.03)`은 너무 약해서 모니터에 따라 안 보입니다. `0.06` 정도로 올리고, 대신 `Dashed` 스타일로 바꿔서 존재감을 낮춥시다."

**✅ Decision**: "차트 컨테이너 배경색 미세 조정 및 그리드 스타일 강화."

---

## 🔄 Loop 8: 데이터 로딩 피드백 (Latency Feedback)

**QT**: "차트를 줌인/줌아웃 할 때 데이터가 로딩 중이면 캔들이 멈춰있는 것처럼 보입니다. **'Loading Spinner'**가 차트 중앙에 떠야 합니다."

**UX**: "중앙 스피너는 너무 올드합니다. 차트 상단에 얇은 **'Progress Bar'**가 지나가거나, 캔들이 살짝 흐려지는(Blur) 효과가 더 세련됩니다."

**DS**: "데이터 끊김(Gap) 구간에는 빗금(Hatched Pattern)이나 회색 배경을 깔아서 '데이터 없음'과 '거래 없음'을 구분해야 합니다."

**✅ Decision**: "로딩 시 차트 Opacity 0.7 + Blur 처리. 데이터 Gap 시각화는 Phase 3로 미룸."

---

## 🔄 Loop 9: 모바일 및 터치 대응

**UX**: "지금 줌 버튼(+, -)이 너무 작습니다. 터치 타겟 기준(44px)에 미달해요. 핀치 줌(Pinch Zoom)이 되더라도 버튼은 좀 더 키워야 합니다."

**QT**: "전 모바일에서도 트레이딩합니다. 버튼 위치가 우상단이면 손가락이 잘 안 닿아요. **우하단(Bottom-Right)**으로 내립시다."

**✅ Decision**: "줌 컨트롤 버튼 크기 확대 및 우하단 배치 검토 (현재는 우상단 유지하되 크기만 키움)."

---

## 🔄 Loop 10: 최종 합의 (Golden Consensus)

**PM (Moderator)**: "10번의 루프를 돌았습니다. 최종 스펙을 정합시다."

1.  **Indicators**: 볼린저 밴드(Area), VWAP(Bold), MA5/20(Thin), Volume MA.
2.  **UX**: Floating Legend(Backdrop Blur), X-Axis Snap Crosshair.
3.  **Visual**: Market Close Line, Prev Close Line, Refined Colors.

**All**: "Approved. This looks like a pro-tool now."

# 🧪 Experiment Registry

본 디렉토리는 순환매 검출 및 추격매수 전략의 모든 실험 결과, 데이터 분석, 백테스트 리포트를 영구히 보존하기 위한 공간입니다.

## 실험 목록
| 날짜 | 실험명 | 담당 페르소나 | 결과 요약 | 리포트 링크 |
| :--- | :--- | :--- | :--- | :--- |
| 2026-01-16 | 가변적 워커 아티처 설계 검증 | Architect | [Pass] 유연성 확보 | [Link](#) |
| - | (진행 예정) 상법개정 앵커링 백테스트 | Data Scientist | - | - |
| - | (진행 예정) 수급 전이 지연 상관성 분석 | Data Scientist | - | - |

---

## 📈 실험 규격
1. **Directory**: `experiments/[YYYYMMDD]_[Experiment_Name]/`
2. **Contents**:
   - `README.md`: 가설, 사용 데이터, 결과 해석.
   - `config.yaml`: 당시 실험 설정.
   - `charts/`: 시각화 결과물.
3. **Commit Rule**: 실험 단위로 완료 시 커밋하며, `master_roadmap.md` 및 `BACKLOG.md`를 갱신한다.

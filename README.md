# Stock Monitoring (Vibe Coding)

영상 OCR 및 틱 데이터를 활용한 주식 섹터 리밸런싱 및 단타 전략 자동화 프로젝트입니다.

## 🚀 프로젝트 개요
이 프로젝트는 오라클 클라우드 프리티어 환경에서 동작하며, 두 가지 핵심 전략을 수행합니다:
1.  **장기 전략**: 뉴스 영상/이미지 OCR 분석을 통한 섹터 리밸런싱 인사이트 도출.
2.  **단기 전략**: 실시간 틱 데이터 수집 및 분석을 통한 단타(Scalping) 전략.

## 📚 문서 (Documentation)
이 프로젝트는 AI 에이전트와의 협업을 중심으로 설계되었습니다.
-   **[프로젝트 컨텍스트 (Anchor)](docs/project_context.md)**: 기술 스택, 아키텍처, 운영 원칙.
-   **[AI 협업 규칙](.ai-rules.md)**: AI 페르소나 및 작업 가이드라인.
-   **[작업 목록](task.md)**: 현재 진행 상황 및 예정된 작업.

## 🛠️ 시작하기 (Getting Started)
### 요구 사항
-   Docker & Docker Compose
-   Python 3.10+

### 설치 및 실행
```bash
# 레포지토리 클론
git clone https://github.com/USERNAME/stock_monitoring.git

# 설정 파일 생성
cp .env.example .env

# 실행 (추후 업데이트)
make up
```

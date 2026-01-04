# Stock Monitoring (Vibe Coding)

뉴스/소셜 텍스트 분석(NLP) 및 틱 데이터를 활용한 주식 섹터 리밸런싱 및 단타 전략 자동화 프로젝트입니다.

## 🚀 프로젝트 개요
> **Note**: 본 프로젝트는 **Google Deepmind Antigravity**를 통해 100% 기획 및 개발된 **파일럿 프로젝트**입니다.

이 프로젝트는 오라클 클라우드 프리티어 환경에서 동작하며, 다음 단계(Step-by-Step)로 진행됩니다:
1.  **1단계 (Data Collection First)**: 고빈도 **틱(Tick) 데이터**의 안정적인 수집 및 적재 파이프라인 구축을 최우선으로 합니다. (매매 로직은 데이터 확보 후 구현)
2.  **2단계 (Short-term Strategy)**: 수집된 틱 데이터를 활용한 스캘핑 전략 구현.
3.  **3단계 (Long-term Strategy)**: 뉴스/소셜 텍스트 분석(NLP)을 통한 섹터 리밸런싱.

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

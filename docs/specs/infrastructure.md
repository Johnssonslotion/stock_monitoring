# 인프라 및 데이터 파이프라인 명세서 (Infrastructure Spec)

**작성일**: 2026-01-04
**담당자**: Architect

## 1. 개요
**Oracle Cloud Free Tier**의 리소스(ARM 4 Core, 24GB RAM)를 최대한 효율적으로 활용하여 **Zero Cost**로 고가용성 시스템을 구축한다.

## 2. 시스템 아키텍처
```mermaid
graph TD
    subgraph Oracle Cloud
        subgraph Docker Host
            Ingest_News[News Collector] -- Cron --> SharedVol[(Logs/Data)]
            Ingest_Tick[Tick Streamer] -- Websocket --> Redis[Redis (Cache)]
            
            Redis --> Analysis[Analysis Worker]
            SharedVol --> Analysis
            
            Analysis --> DB[(File/SQLite)]
            Analysis --> Web[Dashboard (Streamlit/React)]
        end
    end
    
    User -- HTTPS --> Web
```

## 3. 리소스 할당 계획
| 서비스 | 역할 | CPU 할당 | 메모리 할당 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | 데이터 수집 | 0.5 vCPU | 2 GB | 비동기 I/O 위주 |
| **Analysis** | NLP/지표 계산 | 2.0 vCPU | 8 GB | 연산 집중 |
| **Redis** | 틱 데이터 버퍼 | 0.5 vCPU | 4 GB | In-memory DB |
| **Web** | 대시보드 | 0.5 vCPU | 2 GB | 트래픽 적음 |
| **OS/Etc** | 시스템 여유분 | 0.5 vCPU | 8 GB | 버퍼 |

*총합: 4 vCPU / 24 GB RAM (Optimized)*

## 4. 데이터 파이프라인
### 4.1 메시지 큐 (Message Queue)
-   카프카(Kafka) 등 무거운 미들웨어 대신 **Redis Pub/Sub** 또는 **Python `multiprocessing.Queue`**를 사용하여 경량화.
-   **단타**: Redis Pub/Sub (실시간성).
-   **장기**: Cron Job + 로컬 파일 시스템 (배치성).

### 4.2 스토리지
-   **Raw Data**: 저장하지 않음 (비용 절감).
-   **Processed Data**: `SQLite` 또는 `Parquet` 파일로 저장하여 분석 용이성 확보 및 백업 간편화.

## 5. 배포 및 보안
-   **CI/CD**: GitHub Actions를 통해 Docker Image 빌드 후 SSH 배포.
-   **Secrets**: `.env` 파일은 서버에 직접 주입하거나 GitHub Secrets 변수로 관리.

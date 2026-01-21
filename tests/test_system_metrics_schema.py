"""
Test Suite: System Metrics Schema Validation (TS-TYPE-01)

목적: Sentinel이 발행하는 system metrics 데이터가 TimescaleArchiver의 스키마와 타입이 일치하는지 검증

관련 문서:
- FMEA: Section 3.4
- Test Registry: TS-TYPE-01
- Implementation Plan: TEST_IMPLEMENTATION_PLAN.md
"""

import asyncio
import json
import pytest
import asyncpg
from datetime import datetime
import os

# DB 연결 정보
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

# Redis 연결 정보
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")


@pytest.mark.asyncio
async def test_system_metrics_db_schema():
    """
    system_metrics 테이블 스키마 검증
    - labels 컬럼이 jsonb 타입인지 확인
    """
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )

    try:
        # 테이블 존재 확인
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'system_metrics')"
        )
        assert table_exists, "system_metrics table does not exist"

        # 스키마 조회
        schema = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'system_metrics'
            ORDER BY ordinal_position
        """)

        schema_dict = {row['column_name']: row['data_type'] for row in schema}

        # 필수 컬럼 확인
        assert 'time' in schema_dict, "Missing column: time"
        assert 'metric_name' in schema_dict, "Missing column: metric_name"
        assert 'value' in schema_dict, "Missing column: value"
        assert 'labels' in schema_dict, "Missing column: labels"

        # 타입 검증
        assert schema_dict['time'] == 'timestamp with time zone', \
            f"time column should be 'timestamp with time zone', got {schema_dict['time']}"
        assert schema_dict['metric_name'] == 'text', \
            f"metric_name column should be 'text', got {schema_dict['metric_name']}"
        assert schema_dict['value'] == 'double precision', \
            f"value column should be 'double precision', got {schema_dict['value']}"
        assert schema_dict['labels'] == 'jsonb', \
            f"labels column should be 'jsonb', got {schema_dict['labels']}"

        print(f"\n✅ System Metrics Schema Validated:")
        for col, dtype in schema_dict.items():
            print(f"   - {col}: {dtype}")

    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_system_metrics_type_validation():
    """
    Sentinel이 발행하는 system.metrics 데이터 구조가
    TimescaleDB system_metrics 테이블 스키마와 타입이 일치하는지 검증
    """
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )

    try:
        # 테스트용 메시지 (Sentinel이 발행하는 실제 형식)
        test_messages = [
            # Legacy format (host metrics)
            {
                "timestamp": datetime.now().isoformat(),
                "cpu": 30.5,
                "mem": 45.2,
                "disk": 60.0
            },
            # New generic format (container status)
            {
                "timestamp": datetime.now().isoformat(),
                "type": "container_status",
                "value": 1.0,
                "meta": {"container": "test-container", "status": "running"}
            },
            # Redis metrics
            {
                "timestamp": datetime.now().isoformat(),
                "type": "redis_used_memory",
                "value": 1048576.0,
                "meta": {"status": "ok"}
            },
            # Governance metrics
            {
                "timestamp": datetime.now().isoformat(),
                "type": "governance_status",
                "value": 95.0,
                "meta": {
                    "status": "Healthy",
                    "p0_issues": 0,
                    "active_workflows": 10
                }
            }
        ]

        # TimescaleArchiver 로직 시뮬레이션
        for idx, msg in enumerate(test_messages):
            ts = datetime.fromisoformat(msg['timestamp'])

            if 'cpu' in msg and 'mem' in msg:
                # Legacy format - 여러 행으로 분할
                rows = [
                    (ts, 'cpu', float(msg['cpu']), None),
                    (ts, 'memory', float(msg['mem']), None)
                ]
                if 'disk' in msg:
                    rows.append((ts, 'disk', float(msg['disk']), None))

                # 타입 검증
                for row in rows:
                    assert len(row) == 4, "Row must have 4 columns"
                    assert isinstance(row[0], datetime), "time must be datetime"
                    assert isinstance(row[1], str), "metric_name must be str"
                    assert isinstance(row[2], float), "value must be float"
                    assert isinstance(row[3], (type(None), str)), \
                        f"labels must be None or str (json string), got {type(row[3])}"

                # DB INSERT 테스트
                await conn.executemany(
                    "INSERT INTO system_metrics (time, metric_name, value, labels) VALUES ($1, $2, $3, $4)",
                    rows
                )
                print(f"✅ Message {idx+1} (Legacy format): Inserted {len(rows)} rows")

            else:
                # New generic format
                m_type = msg.get('type')
                val = float(msg.get('value'))

                # CRITICAL: meta를 json.dumps로 변환해야 함
                labels = json.dumps(msg.get('meta')) if msg.get('meta') else None

                # 타입 검증
                assert isinstance(m_type, str), f"type must be str, got {type(m_type)}"
                assert isinstance(val, float), f"value must be float, got {type(val)}"
                assert isinstance(labels, (type(None), str)), \
                    f"labels must be None or str (json.dumps result), got {type(labels)}"

                # json.dumps 결과가 valid JSON인지 확인
                if labels:
                    try:
                        json.loads(labels)
                    except json.JSONDecodeError as e:
                        pytest.fail(f"labels is not valid JSON: {e}")

                # DB INSERT 테스트
                try:
                    await conn.execute(
                        "INSERT INTO system_metrics (time, metric_name, value, labels) VALUES ($1, $2, $3, $4)",
                        ts, m_type, val, labels
                    )
                    print(f"✅ Message {idx+1} ({m_type}): Inserted successfully")
                except Exception as e:
                    pytest.fail(f"Failed to insert metric '{m_type}': {e}")

        # 삽입된 데이터 검증
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM system_metrics WHERE time > NOW() - INTERVAL '1 minute'"
        )
        assert count >= len(test_messages), \
            f"Expected at least {len(test_messages)} rows, got {count}"

        print(f"\n✅ All {count} metrics inserted successfully")

        # 샘플 데이터 조회 및 타입 확인
        sample = await conn.fetch(
            "SELECT metric_name, value, labels FROM system_metrics WHERE time > NOW() - INTERVAL '1 minute' LIMIT 5"
        )

        print("\n📊 Sample Inserted Data:")
        for row in sample:
            print(f"   - {row['metric_name']}: {row['value']} | labels: {row['labels']}")

            # labels가 jsonb 타입인지 확인 (dict로 반환됨)
            if row['labels'] is not None:
                assert isinstance(row['labels'], (dict, str)), \
                    f"labels should be dict or str, got {type(row['labels'])}"

    finally:
        # 테스트 데이터 정리
        await conn.execute(
            "DELETE FROM system_metrics WHERE time > NOW() - INTERVAL '1 minute'"
        )
        await conn.close()


@pytest.mark.asyncio
async def test_sentinel_publisher_validation():
    """
    Sentinel이 실제로 발행하는 메시지를 subscribe하여 타입 검증
    (실제 시스템이 실행 중일 때만 테스트)
    """
    try:
        from redis.asyncio import Redis
    except ImportError:
        pytest.skip("redis package not installed")

    try:
        redis = await Redis.from_url(REDIS_URL, decode_responses=True)
        await redis.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    pubsub = redis.pubsub()
    await pubsub.subscribe("system.metrics")

    received = []

    async def collect_messages():
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    received.append(data)

                    # Validation
                    assert 'timestamp' in data, "timestamp field is required"

                    # timestamp가 ISO format인지 확인
                    try:
                        datetime.fromisoformat(data['timestamp'])
                    except ValueError:
                        pytest.fail(f"Invalid timestamp format: {data['timestamp']}")

                    # meta 필드가 있으면 dict 타입이어야 함 (발행 시점)
                    if 'meta' in data:
                        assert isinstance(data['meta'], dict), \
                            f"meta must be dict at publish time, got {type(data['meta'])}"
                        print(f"✅ Received metric: {data.get('type', 'legacy')} | meta: {data['meta']}")

                    if len(received) >= 3:  # 3개 메시지 수신 후 종료
                        break
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in message: {e}")

    try:
        await asyncio.wait_for(collect_messages(), timeout=30)
    except asyncio.TimeoutError:
        pytest.skip("No system metrics published within 30 seconds (system may not be running)")
    finally:
        await redis.close()

    assert len(received) > 0, "Should receive at least one metric"
    print(f"\n✅ Successfully validated {len(received)} real-time metrics")


@pytest.mark.asyncio
async def test_archiver_error_handling():
    """
    타입 불일치 데이터가 들어왔을 때 Archiver가 에러를 발생시키는지 검증
    """
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )

    try:
        # 잘못된 타입 (dict를 직접 전달)
        invalid_message = {
            "timestamp": datetime.now(),
            "type": "test_metric",
            "value": 100.0,
            "meta": {"key": "value"}  # dict를 그대로 전달 (잘못됨)
        }

        ts = invalid_message['timestamp']
        m_type = invalid_message['type']
        val = invalid_message['value']
        labels = invalid_message['meta']  # dict를 그대로 전달

        # 에러 발생 예상
        with pytest.raises(Exception) as exc_info:
            await conn.execute(
                "INSERT INTO system_metrics (time, metric_name, value, labels) VALUES ($1, $2, $3, $4)",
                ts, m_type, val, labels
            )

        print(f"\n✅ Correctly rejected invalid type: {exc_info.value}")
        assert "expected str, got dict" in str(exc_info.value) or \
               "invalid input" in str(exc_info.value).lower(), \
            "Should reject dict type for labels column"

    finally:
        await conn.close()


if __name__ == "__main__":
    # 직접 실행 시 테스트 실행
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

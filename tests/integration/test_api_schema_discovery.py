"""
API Schema Discovery Test
==========================

목적: 각 TR ID별 실제 API 응답 스키마를 수집하여 문서화

⚠️ 실제 API 호출이 필요하므로 수동 실행 전용:
   PYTHONPATH=. poetry run pytest tests/integration/test_api_schema_discovery.py -v -s -m manual

전제조건:
- KIS_APP_KEY, KIS_APP_SECRET 환경변수 설정
- KIWOOM_API_KEY, KIWOOM_SECRET_KEY 환경변수 설정
- Redis 실행 중 (localhost:6379)
- Rate Limiter (redis-gatekeeper) 실행 중

출력:
- 각 TR ID별 응답 JSON 구조를 파일로 저장
- docs/specs/api_reference/schemas/ 디렉토리에 저장
"""
import pytest
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from src.api_gateway.hub.client import APIHubClient


# 테스트 대상 TR ID 목록
TEST_CASES = [
    # KIS - 기존
    {
        "provider": "KIS",
        "tr_id": "FHKST01010300",
        "description": "국내주식 시간별체결 (틱 데이터)",
        "params": {
            "symbol": "005930",  # 삼성전자
            "time": "150000"     # 15:00:00
        }
    },
    {
        "provider": "KIS",
        "tr_id": "FHKST01010400",
        "description": "국내주식 현재가 분봉",
        "params": {
            "symbol": "005930"
        }
    },
    {
        "provider": "KIS",
        "tr_id": "FHKST03010200",
        "description": "국내주식 기간별 분봉",
        "params": {
            "symbol": "005930",
            "time": "150000"
        }
    },
    {
        "provider": "KIS",
        "tr_id": "HHDFS76950200",
        "description": "해외주식 기간별 분봉",
        "params": {
            "EXCD": "NAS",
            "SYMB": "AAPL",
            "GUBN": "0",
            "BYMD": datetime.now().strftime("%Y%m%d"),
            "MODP": "1"
        }
    },
    # KIS - Pillar 8: Market Intelligence (신규)
    {
        "provider": "KIS",
        "tr_id": "FHKST01010900",
        "description": "[Pillar8] 주식현재가 투자자 (외국인/기관/개인)",
        "params": {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": "005930"  # 삼성전자
        }
    },
    {
        "provider": "KIS",
        "tr_id": "FHKST01060200",
        "description": "[Pillar8] 종목별 외국계 순매수추이",
        "params": {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": "005930"
        }
    },
    {
        "provider": "KIS",
        "tr_id": "FHKST01060500",
        "description": "[Pillar8] 국내주식 공매도 일별추이",
        "params": {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": "005930"
        }
    },
    {
        "provider": "KIS",
        "tr_id": "FHKST01060600",
        "description": "[Pillar8] 프로그램매매 종목별 추이",
        "params": {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": "005930"
        }
    },
    # Kiwoom
    {
        "provider": "KIWOOM",
        "tr_id": "ka10080",
        "description": "국내주식 분봉 조회",
        "params": {
            "symbol": "005930",
            "timeframe": "1"
        }
    },
    {
        "provider": "KIWOOM",
        "tr_id": "ka10079",
        "description": "국내주식 틱 조회",
        "params": {
            "symbol": "005930",
            "tick_unit": "1"
        }
    }
]


OUTPUT_DIR = Path("docs/specs/api_reference/schemas")


@pytest.fixture
async def hub_client():
    """API Hub Client fixture"""
    client = APIHubClient()
    await client.connect()
    yield client
    await client.disconnect()


def save_schema(provider: str, tr_id: str, description: str, params: Dict, response: Dict):
    """
    API 응답 스키마를 파일로 저장
    
    Args:
        provider: Provider 이름 (KIS/KIWOOM)
        tr_id: TR ID
        description: 설명
        params: 요청 파라미터
        response: API 응답
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = OUTPUT_DIR / f"{provider.lower()}_{tr_id.lower()}_schema.json"
    
    schema_doc = {
        "provider": provider,
        "tr_id": tr_id,
        "description": description,
        "collected_at": datetime.now().isoformat(),
        "request_params": params,
        "response": response,
        "schema_analysis": analyze_schema(response)
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(schema_doc, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Schema saved: {filename}")


def analyze_schema(data: Any, path: str = "") -> Dict[str, Any]:
    """
    응답 데이터 구조 분석
    
    Args:
        data: 분석할 데이터
        path: 현재 경로 (재귀용)
    
    Returns:
        스키마 분석 결과
    """
    if isinstance(data, dict):
        return {
            "type": "object",
            "fields": {
                key: analyze_schema(value, f"{path}.{key}" if path else key)
                for key, value in data.items()
            }
        }
    elif isinstance(data, list):
        if len(data) > 0:
            return {
                "type": "array",
                "item_count": len(data),
                "sample_item": analyze_schema(data[0], f"{path}[0]")
            }
        else:
            return {
                "type": "array",
                "item_count": 0,
                "sample_item": None
            }
    elif isinstance(data, str):
        return {"type": "string", "example": data}
    elif isinstance(data, int):
        return {"type": "integer", "example": data}
    elif isinstance(data, float):
        return {"type": "float", "example": data}
    elif isinstance(data, bool):
        return {"type": "boolean", "example": data}
    elif data is None:
        return {"type": "null"}
    else:
        return {"type": str(type(data)), "example": str(data)}


@pytest.mark.manual
@pytest.mark.asyncio
async def test_discover_all_schemas(hub_client):
    """
    모든 TR ID의 스키마 수집
    
    각 TR ID별로:
    1. API Hub를 통해 실제 API 호출
    2. 응답 수신
    3. 스키마 분석
    4. JSON 파일로 저장
    """
    results = []
    
    print("\n" + "="*80)
    print("API Schema Discovery Test")
    print("="*80 + "\n")
    
    for i, test_case in enumerate(TEST_CASES, 1):
        provider = test_case["provider"]
        tr_id = test_case["tr_id"]
        description = test_case["description"]
        params = test_case["params"]
        
        print(f"\n[{i}/{len(TEST_CASES)}] Testing {provider} - {tr_id}")
        print(f"Description: {description}")
        print(f"Params: {json.dumps(params, indent=2)}")
        
        try:
            # API Hub를 통해 호출
            result = await hub_client.execute(
                provider=provider,
                tr_id=tr_id,
                params=params,
                timeout=15.0
            )
            
            status = result.get("status")
            
            if status == "SUCCESS":
                data = result.get("data", {})
                print(f"✅ SUCCESS")
                print(f"Response keys: {list(data.keys())}")
                
                # 스키마 저장
                save_schema(provider, tr_id, description, params, data)
                
                results.append({
                    "provider": provider,
                    "tr_id": tr_id,
                    "status": "SUCCESS",
                    "response_keys": list(data.keys())
                })
                
            elif status == "RATE_LIMITED":
                print(f"⏳ RATE_LIMITED - Waiting 5 seconds...")
                await asyncio.sleep(5)
                
                # Retry
                result = await hub_client.execute(
                    provider=provider,
                    tr_id=tr_id,
                    params=params,
                    timeout=15.0
                )
                
                if result.get("status") == "SUCCESS":
                    data = result.get("data", {})
                    save_schema(provider, tr_id, description, params, data)
                    results.append({
                        "provider": provider,
                        "tr_id": tr_id,
                        "status": "SUCCESS (retry)",
                        "response_keys": list(data.keys())
                    })
                else:
                    print(f"❌ FAILED after retry: {result.get('reason')}")
                    results.append({
                        "provider": provider,
                        "tr_id": tr_id,
                        "status": "FAILED",
                        "reason": result.get("reason")
                    })
                    
            else:
                print(f"❌ FAILED: {result.get('reason')}")
                results.append({
                    "provider": provider,
                    "tr_id": tr_id,
                    "status": "FAILED",
                    "reason": result.get("reason")
                })
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            results.append({
                "provider": provider,
                "tr_id": tr_id,
                "status": "EXCEPTION",
                "error": str(e)
            })
    
    # 최종 결과 출력
    print("\n" + "="*80)
    print("Test Results Summary")
    print("="*80 + "\n")
    
    success_count = sum(1 for r in results if "SUCCESS" in r.get("status", ""))
    
    for result in results:
        status_icon = "✅" if "SUCCESS" in result.get("status", "") else "❌"
        print(f"{status_icon} {result['provider']:8s} {result['tr_id']:20s} - {result['status']}")
    
    print(f"\n📊 Success Rate: {success_count}/{len(TEST_CASES)}")
    
    # 문서 생성 트리거
    generate_schema_documentation(results)


def generate_schema_documentation(results: list):
    """
    수집된 스키마를 기반으로 마크다운 문서 생성
    
    Args:
        results: 테스트 결과 리스트
    """
    doc_path = OUTPUT_DIR / "README.md"
    
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("# API Response Schemas\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n\n")
        f.write("---\n\n")
        f.write("## Overview\n\n")
        f.write("본 디렉토리는 각 증권사 REST API의 실제 응답 스키마를 포함합니다.\n\n")
        f.write("**수집 방법**: API Hub v2를 통한 실제 API 호출\n\n")
        f.write("---\n\n")
        f.write("## Schema Files\n\n")
        
        # KIS
        f.write("### KIS (한국투자증권)\n\n")
        f.write("| TR ID | Description | Status | File |\n")
        f.write("|-------|-------------|--------|------|\n")
        
        for result in results:
            if result["provider"] == "KIS":
                tr_id = result["tr_id"]
                status = result["status"]
                status_icon = "✅" if "SUCCESS" in status else "❌"
                filename = f"{result['provider'].lower()}_{tr_id.lower()}_schema.json"
                
                # TEST_CASES에서 description 찾기
                desc = next(
                    (tc["description"] for tc in TEST_CASES if tc["tr_id"] == tr_id),
                    "N/A"
                )
                
                f.write(f"| `{tr_id}` | {desc} | {status_icon} {status} | [{filename}](./{filename}) |\n")
        
        f.write("\n")
        
        # Kiwoom
        f.write("### Kiwoom (키움증권)\n\n")
        f.write("| API ID | Description | Status | File |\n")
        f.write("|--------|-------------|--------|------|\n")
        
        for result in results:
            if result["provider"] == "KIWOOM":
                tr_id = result["tr_id"]
                status = result["status"]
                status_icon = "✅" if "SUCCESS" in status else "❌"
                filename = f"{result['provider'].lower()}_{tr_id.lower()}_schema.json"
                
                desc = next(
                    (tc["description"] for tc in TEST_CASES if tc["tr_id"] == tr_id),
                    "N/A"
                )
                
                f.write(f"| `{tr_id}` | {desc} | {status_icon} {status} | [{filename}](./{filename}) |\n")
        
        f.write("\n")
        f.write("---\n\n")
        f.write("## Usage\n\n")
        f.write("각 스키마 파일은 다음 정보를 포함합니다:\n\n")
        f.write("```json\n")
        f.write("{\n")
        f.write('  "provider": "Provider 이름",\n')
        f.write('  "tr_id": "TR ID",\n')
        f.write('  "description": "설명",\n')
        f.write('  "collected_at": "수집 시간 (ISO 8601)",\n')
        f.write('  "request_params": { /* 요청 파라미터 */ },\n')
        f.write('  "response": { /* 실제 API 응답 */ },\n')
        f.write('  "schema_analysis": { /* 스키마 구조 분석 */ }\n')
        f.write("}\n")
        f.write("```\n\n")
        f.write("---\n\n")
        f.write("## Related Documents\n\n")
        f.write("- [KIS TR ID Reference](../kis_tr_id_reference.md)\n")
        f.write("- [Kiwoom TR ID Reference](../kiwoom_tr_id_reference.md)\n")
        f.write("- [Ground Truth Policy](../../../governance/ground_truth_policy.md)\n")
    
    print(f"\n📄 Documentation generated: {doc_path}")


@pytest.mark.manual
@pytest.mark.asyncio
async def test_single_schema_kis_tick(hub_client):
    """
    단일 TR ID 테스트 (KIS 틱 데이터)
    
    디버깅용 개별 테스트
    """
    test_case = TEST_CASES[0]  # FHKST01010300
    
    print(f"\nTesting: {test_case['tr_id']} - {test_case['description']}")
    
    result = await hub_client.execute(
        provider=test_case["provider"],
        tr_id=test_case["tr_id"],
        params=test_case["params"],
        timeout=15.0
    )
    
    print(f"\nStatus: {result.get('status')}")
    
    if result.get("status") == "SUCCESS":
        data = result.get("data", {})
        print(f"Response keys: {list(data.keys())}")
        print(f"\nFull response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Schema 저장
        save_schema(
            test_case["provider"],
            test_case["tr_id"],
            test_case["description"],
            test_case["params"],
            data
        )
    else:
        print(f"Reason: {result.get('reason')}")
        pytest.fail(f"API call failed: {result.get('reason')}")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "-m", "manual"]))

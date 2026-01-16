import json
import sys
import os

# 워크스페이스 루트를 패스에 추가하여 모듈 임포트 가능케 함
sys.path.append(os.getcwd())

from src.data_ingestion.price.schemas.mirae import MiraeWSResponse, ACTUAL_SAMPLE_WS_DATA
from src.data_ingestion.price.schemas.kiwoom_re import KiwoomRealData, ACTUAL_SAMPLE_TR_DATA
from pydantic import ValidationError

def validate_mirae():
    print("🔍 Validating Mirae Asset Sample Data...")
    try:
        validated = MiraeWSResponse(**ACTUAL_SAMPLE_WS_DATA)
        print(f"✅ Mirae Validation Success: {validated.tr_key} price is {validated.data.stck_prpr}")
    except ValidationError as e:
        print(f"❌ Mirae Validation Failed: {e}")

def validate_kiwoom():
    print("\n🔍 Validating Kiwoom RE Sample Data...")
    # Kiwoom Real Data는 FID 기반이므로 별도 매핑 검증 필요
    sample_real = {
        "symbol": "005930",
        "10": "73200", # 현재가
        "11": "500",   # 대비
        "15": "12500000", # 거래량
        "20": "153000"  # 시간
    }
    try:
        validated = KiwoomRealData(**sample_real)
        print(f"✅ Kiwoom Validation Success: {validated.symbol} price is {validated.price}")
    except ValidationError as e:
        print(f"❌ Kiwoom Validation Failed: {e}")

if __name__ == "__main__":
    validate_mirae()
    validate_kiwoom()

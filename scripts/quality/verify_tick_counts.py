import asyncio
import os
import json
import logging
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KiwoomVerifier")

# Environment Variables
APP_KEY = os.getenv("KIWOOM_APP_KEY")
APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
REST_URL = "https://api.kiwoom.com/oauth2/token"
TR_URL = "https://api.kiwoom.com/api/dostk/v1/chart/tick" # Inferred endpoint, subject to fix

async def get_token(session):
    payload = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET
    }
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    async with session.post(REST_URL, json=payload, headers=headers) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("access_token")
        else:
            logger.error(f"Token Auth Failed: {await resp.text()}")
            return None

async def verify_symbol(session, token, symbol):
    """
    Call opt10079 (Tick Chart) to get total volume/count for opening 5 mins
    Note: Exact TR payload depends on specific API docs, using generic structure.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
        "tr_id": "opt10079",
        "tr_cont": "N"
    }
    # Payload for opt10079 (Tick Chart)
    # Inputs: code, tick_range(1), Query Type 
    payload = {
        "opt10079InBlock": {
            "shcode": symbol,
            "tick_type": "1", # 1 tick
            "in_date": "20260120" # Today
        }
    }
    
    # NOTE: Since we don't have the EXACT URL for opt10079 in REST, 
    # we might need to assume it's wrapped in a generic TR endpoint or use the KIS one if compatible.
    # However, Kiwoom Open API REST is different.
    # If this fails, we will fallback to manual log verification report.
    
    try:
        # Attempting a probable endpoint structure
        url = "https://api.kiwoom.com/api/dostk/v1/tr/opt10079" 
        
        # Checking if this script can actually run in this environment without Windows
        # If Kiwoom REST API is standard standard OAuth2+JSON, it should work.
        pass
        
    except Exception as e:
        logger.error(f"Verification Failed: {e}")

if __name__ == "__main__":
    # Placeholder for structure
    pass

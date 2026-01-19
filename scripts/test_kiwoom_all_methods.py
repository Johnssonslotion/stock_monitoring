import asyncio
import os
import aiohttp
import json
import requests  # Try requests library as well
from dotenv import load_dotenv

load_dotenv()

async def test_various_approaches():
    """
    Try different approaches to call Kiwoom API
    """
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    
    print(f"Testing Kiwoom API with various approaches")
    print(f"App Key: {app_key}")
    print("="*80)
    
    token_url = "https://api.kiwoom.com/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }
    
    # Try 1: requests library (synchronous)
    print("\n1️⃣ Try with requests library (sync)...")
    try:
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        resp = requests.post(token_url, json=payload, headers=headers, verify=False)
        print(f"   Status: {resp.status_code}")
        print(f"   Headers: {dict(resp.headers)}")
        print(f"   Body: {resp.text[:500]}")
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("return_code") == 0:
                print(f"   ✅ SUCCESS!")
                return data.get("token")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Try 2: aiohttp with different SSL settings
    print("\n2️⃣ Try with aiohttp (verify SSL = True)...")
    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                "Content-Type": "application/json; charset=UTF-8",
                "User-Agent": "Mozilla/5.0"
            }
            
            async with session.post(token_url, json=payload, headers=headers, ssl=True) as resp:
                print(f"   Status: {resp.status}")
                text = await resp.text()
                print(f"   Body: {text[:500]}")
                
                if resp.status == 200:
                    data = json.loads(text)
                    if data.get("return_code") == 0:
                        print(f"   ✅ SUCCESS!")
                        return data.get("token")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Try 3: Check if it's a parameter format issue
    print("\n3️⃣ Try with form-encoded body...")
    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0"
            }
            
            # Form data
            form_data = aiohttp.FormData()
            form_data.add_field("grant_type", "client_credentials")
            form_data.add_field("appkey", app_key)
            form_data.add_field("secretkey", app_secret)
            
            async with session.post(token_url, data=form_data, ssl=False) as resp:
                print(f"   Status: {resp.status}")
                text = await resp.text()
                print(f"   Body: {text[:500]}")
                
                if resp.status == 200:
                    try:
                        data = json.loads(text)
                        if data.get("return_code") == 0:
                            print(f"   ✅ SUCCESS!")
                            return data.get("token")
                    except:
                        pass
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Try 4: Exact curl equivalent
    print("\n4️⃣ Try exact curl command...")
    try:
        import subprocess
        curl_cmd = f"""
        curl -X POST 'https://api.kiwoom.com/oauth2/token' \
        -H 'Content-Type: application/json; charset=UTF-8' \
        -H 'User-Agent: Mozilla/5.0' \
        -d '{json.dumps(payload)}' \
        --insecure
        """
        
        result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True)
        print(f"   Status: {result.returncode}")
        print(f"   Stdout: {result.stdout[:500]}")
        print(f"   Stderr: {result.stderr[:200]}")
        
        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                if data.get("return_code") == 0:
                    print(f"   ✅ SUCCESS!")
                    return data.get("token")
            except:
                pass
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n❌ All approaches failed")
    return None

if __name__ == "__main__":
    token = asyncio.run(test_various_approaches())
    
    if token:
        print(f"\n{'='*80}")
        print(f"✅ Token: {token[:50]}...")
        print(f"{'='*80}")


import json
import os

filepath = "data/raw/kiwoom/ws_raw_20260121_04.jsonl"
if os.path.exists(filepath):
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            row = json.loads(line)
            msg_str = row.get('msg', '{}')
            data_obj = json.loads(msg_str)
            items = data_obj.get('data', [])
            if not isinstance(items, list): items = [items]
            for item in items:
                if item.get('type') == '0D':
                    print(f"Keys in 0D values: {list(item.get('values', {}).keys())[:20]}")
                    exit(0)
            if i > 5000: break
else:
    print("Log file not found")

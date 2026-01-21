
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
                print(f"Index {i}, Type: {item.get('type')}, Item: {item.get('item')}")
                if item.get('type') == '0D':
                    print(f"Sample 0D: {json.dumps(item, indent=2)}")
                    exit(0)
            if i > 1000: break
else:
    print("Log file not found")

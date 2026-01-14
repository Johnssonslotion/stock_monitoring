#!/usr/bin/env python3
"""
저장된 Docker 로그에서 WebSocket 메시지 재생 및 분석
장애 발생 시 실제 메시지를 로컬에서 재실험 가능
"""
import re
import json
import sys
from datetime import datetime

def parse_raw_messages(log_file):
    """로그에서 📨 RAW MSG 추출"""
    messages = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            # DEBUG:websocket_base:📨 RAW MSG: {actual message}
            if '📨 RAW MSG:' in line:
                try:
                    # 메시지 부분 추출
                    msg_start = line.find('📨 RAW MSG:') + len('📨 RAW MSG:')
                    raw_msg = line[msg_start:].strip()
                    
                    # 타임스탬프 추출 (로그 라인 시작 부분)
                    timestamp = line[:23] if len(line) > 23 else None
                    
                    messages.append({
                        'timestamp': timestamp,
                        'raw': raw_msg,
                        'type': 'json' if raw_msg.startswith('{') else 'pipe'
                    })
                except Exception as e:
                    print(f"Parse error: {e}")
    
    return messages

def analyze_messages(messages):
    """메시지 통계 분석"""
    json_count = sum(1 for m in messages if m['type'] == 'json')
    pipe_count = sum(1 for m in messages if m['type'] == 'pipe')
    
    print(f"Total messages: {len(messages)}")
    print(f"  JSON: {json_count}")
    print(f"  Pipe-delimited: {pipe_count}")
    
    if json_count > 0:
        print("\nJSON messages (first 5):")
        for msg in [m for m in messages if m['type'] == 'json'][:5]:
            try:
                data = json.loads(msg['raw'])
                msg_type = data.get('body', {}).get('msg1', 'Unknown')
                print(f"  {msg['timestamp']}: {msg_type}")
            except:
                print(f"  {msg['timestamp']}: (parse failed)")
    
    if pipe_count > 0:
        print(f"\nPipe-delimited messages: {pipe_count}")
        print("  (Actual tick data)")

def replay_for_testing(messages, output_file):
    """테스트용 메시지 재생 파일 생성"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, msg in enumerate(messages):
            f.write(f"# Message {i+1} at {msg['timestamp']}\n")
            f.write(f"{msg['raw']}\n\n")
    
    print(f"\n✅ Saved {len(messages)} messages to {output_file}")
    print(f"   Use this for offline parsing tests")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python replay_logs.py <log_file>")
        print("Example: python replay_logs.py logs/docker/real-collector_20260109.log")
        sys.exit(1)
    
    log_file = sys.argv[1]
    print(f"Analyzing: {log_file}\n")
    
    messages = parse_raw_messages(log_file)
    analyze_messages(messages)
    
    if messages:
        output = log_file.replace('.log', '_messages.txt')
        replay_for_testing(messages, output)

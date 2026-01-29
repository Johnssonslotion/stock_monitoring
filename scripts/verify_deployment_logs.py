#!/usr/bin/env python3
"""
Deployment Log Verification Script (RFC-006)
===========================================

Checks docker logs for critical errors after deployment.
Usage: python3 verify_deployment_logs.py [--duration 30]

Exit Code:
    0: Clean logs (Success)
    1: Critical errors found (Failure)
"""
import subprocess
import time
import re
import sys
import argparse
from typing import List, Dict

# Configuration
CONTAINERS = [
    "verification-worker",
    "stock_prod-gateway-worker-real",
    "tick-archiver",
    "news-collector",
    "sentinel-agent"
]

# Error Patterns (Regex)
CRITICAL_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r"ModuleNotFoundError",
    r"ImportError",
    r"NameError",
    r"SyntaxError",
    r"IndentationError",
    r"ConnectionRefusedError.*Redis",  # Redis Connection Fail
    r"asyncpg\.exceptions\..*",        # DB Connection Fail
    r"CRITICAL",
    r"FATAL"
]

# Warning Patterns (Non-blocking but notable)
WARNING_PATTERNS = [
    r"WARNING",
    r"Zero Data Received",
    r"Deprecated"
]

def get_container_logs(container: str, duration_sec: int) -> str:
    """Get logs for the last N seconds"""
    try:
        # Check if container is running
        status = subprocess.check_output(
            ["docker", "inspect", "--format", "{{.State.Status}}", container],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        
        if status != "running":
            return f"CONTAINER NOT RUNNING (Status: {status})"

        # Get logs since duration_sec ago
        # Note: --since accepts timestamp or duration (e.g. 30s)
        cmd = ["docker", "logs", "--since", f"{duration_sec}s", container]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout + result.stderr
    except subprocess.CalledProcessError:
        return "CONTAINER NOT FOUND"

def check_logs(duration: int):
    print(f"🔍 Verifying deployment logs (Last {duration}s)...")
    
    failure_count = 0
    warning_count = 0
    
    for container in CONTAINERS:
        print(f"  Checking {container}...", end=" ", flush=True)
        logs = get_container_logs(container, duration)
        
        if logs.startswith("CONTAINER"):
            print(f"❌ {logs}")
            failure_count += 1
            continue

        errors = []
        warnings = []
        
        for line in logs.splitlines():
            # Check Critical
            for pattern in CRITICAL_PATTERNS:
                if re.search(pattern, line):
                    errors.append(line.strip())
                    break # Count line once
            
            # Check Warning (if not error)
            if not errors and any(re.search(p, line) for p in WARNING_PATTERNS):
                warnings.append(line.strip())

        if errors:
            print(f"❌ FAILED ({len(errors)} errors)")
            for e in errors[:3]: # Show first 3
                print(f"    - {e}")
            failure_count += 1
        elif warnings:
            print(f"⚠️  WARNING ({len(warnings)} warnings)")
            warning_count += 1
        else:
            print("✅ Clean")
            
    print("-" * 40)
    if failure_count > 0:
        print(f"❌ Verification FAILED: {failure_count} containers have critical errors.")
        sys.exit(1)
    else:
        print(f"✅ Verification PASSED. (Warnings: {warning_count})")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Deployment Logs")
    parser.add_argument("--duration", type=int, default=30, help="Seconds of logs to scan (default: 30)")
    args = parser.parse_args()
    
    check_logs(args.duration)

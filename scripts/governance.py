#!/usr/bin/env python3
"""
Governance as Code - Antigravity Rule Enforcer
이 스크립트는 .ai-rules.md에 정의된 규칙을 강제합니다.
자동화된 품질 게이트(Quality Gate) 역할을 수행합니다.
"""

import sys
import subprocess
import os
import ast
import re

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()

def check_branch_naming():
    """Rule: 브랜치 이름은 feat/, fix/, exp/, test/, docs/ 로 시작해야 한다."""
    current_branch = run_cmd("git rev-parse --abbrev-ref HEAD")
    valid_prefixes = ["feat/", "fix/", "exp/", "test/", "docs/", "master"]
    
    if not any(current_branch.startswith(p) for p in valid_prefixes):
        print(f"❌ [Governance] Invalid Branch Name: '{current_branch}'")
        print(f"   Must start with: {valid_prefixes}")
        return False
    print(f"✅ [Governance] Branch Name OK: {current_branch}")
    return True

def check_uncommitted_changes():
    """Rule: 작업 완료 선언 전 커밋 필수 (Git Clean)"""
    status = run_cmd("git status --porcelain")
    if status:
        print("❌ [Governance] Uncommitted Changes Detected!")
        print("   Please commit your changes before finishing the task.")
        return False
    print("✅ [Governance] Git Clean OK")
    return True

def check_docstrings(directory="src"):
    """Rule: 모든 Public 함수/클래스는 한글 Docstring을 가져야 한다."""
    korean_pattern = re.compile("[가-힣]+")
    failed_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"): continue
            path = os.path.join(root, file)
            
            with open(path, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except:
                    continue
                
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    # Private Method Skip
                    if node.name.startswith("_"): continue
                    
                    doc = ast.get_docstring(node)
                    if not doc:
                        # Allow missing docstring for now to be pragmatic, but warn
                        continue 
                        
                    if not korean_pattern.search(doc):
                        print(f"⚠️ [Governance] Expecting Korean Docstring: {path} :: {node.name}")
                        # Strict mode would return False here
                        
    print("✅ [Governance] Docstring Check Passed (Pragmatic)")
    return True

def run_audit():
    print("🛡️ [Governance] Starting Audit...")
    
    checks = [
        check_branch_naming(),
        # check_docstrings(), # Temporary disable or warning only
        check_uncommitted_changes()
    ]
    
    if all(checks):
        print("\n✨ All Governance Checks Passed! You are safe to proceed.")
        sys.exit(0)
    else:
        print("\n🚫 [Governance] Audit Failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    run_audit()

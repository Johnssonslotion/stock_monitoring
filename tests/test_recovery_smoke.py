#!/usr/bin/env python3
"""
[ISSUE-031] Quick Smoke Test for Recovery Modules
Verifies basic imports and functionality without external dependencies
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Test all recovery module imports"""
    print("🧪 Testing module imports...")
    
    try:
        from src.data_ingestion.recovery.log_recovery import LogRecoveryManager
        print("✅ log_recovery.LogRecoveryManager")
    except Exception as e:
        print(f"❌ log_recovery import failed: {e}")
        return False
    
    try:
        from src.data_ingestion.recovery.backfill_manager import BackfillManager
        print("✅ backfill_manager.BackfillManager")
    except Exception as e:
        print(f"❌ backfill_manager import failed: {e}")
        return False
    
    try:
        from src.data_ingestion.recovery.recovery_orchestrator import RecoveryOrchestrator
        print("✅ recovery_orchestrator.RecoveryOrchestrator")
    except Exception as e:
        print(f"❌ recovery_orchestrator import failed: {e}")
        return False
    
    return True

def test_log_recovery_init():
    """Test LogRecoveryManager initialization"""
    print("\n🧪 Testing LogRecoveryManager init...")
    
    try:
        from src.data_ingestion.recovery.log_recovery import LogRecoveryManager
        
        # Create instance with test paths
        manager = LogRecoveryManager(
            db_path="/tmp/test_recovery.duckdb",
            log_dir="data/raw/kiwoom"
        )
        
        print("✅ LogRecoveryManager initialized successfully")
        return True
    except Exception as e:
        print(f"❌ LogRecoveryManager init failed: {e}")
        return False

def test_backfill_manager_init():
    """Test BackfillManager initialization (without actual API calls)"""
    print("\n🧪 Testing BackfillManager init...")
    
    try:
        from src.data_ingestion.recovery.backfill_manager import BackfillManager
        
        # Create instance with minimal symbols
        manager = BackfillManager(target_symbols=["005930"])
        
        print(f"✅ BackfillManager initialized (temp DB: {manager.db_path})")
        
        # Cleanup temp file
        import os
        if os.path.exists(manager.db_path):
            os.remove(manager.db_path)
            print("🧹 Cleaned up temp DB")
        
        return True
    except Exception as e:
        print(f"❌ BackfillManager init failed: {e}")
        return False

def main():
    print("=" * 60)
    print("ISSUE-031 Recovery Modules Smoke Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("LogRecoveryManager Init", test_log_recovery_init()))
    results.append(("BackfillManager Init", test_backfill_manager_init()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All smoke tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

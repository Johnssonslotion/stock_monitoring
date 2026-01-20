#!/usr/bin/env python3
"""
Pre-flight Health Check Script
Run this before market open (08:30 KST) to ensure all critical systems are operational.

Usage:
    python scripts/preflight_check.py
    
Exit Codes:
    0: All checks passed
    1: Critical failure detected
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Tuple
import subprocess


class HealthCheck:
    """System health check orchestrator"""
    
    def __init__(self):
        self.failures: List[str] = []
        self.warnings: List[str] = []
        
    def log(self, emoji: str, message: str):
        """Formatted logging"""
        print(f"{emoji} {message}")
        
    async def check_python_imports(self) -> bool:
        """Verify all critical Python imports work"""
        self.log("🔍", "Checking Python Dependencies...")
        
        critical_imports = [
            "redis.asyncio",
            "websockets",
            "psycopg2",
            "httpx",
            "pandas",
            "pydantic",
        ]
        
        for module in critical_imports:
            try:
                __import__(module)
                self.log("  ✅", f"{module}")
            except ImportError as e:
                self.failures.append(f"Missing module: {module}")
                self.log("  ❌", f"{module} - {e}")
                return False
                
        return True
    
    async def check_redis_connection(self) -> bool:
        """Test Redis connectivity"""
        self.log("🔍", "Checking Redis Connection...")
        
        try:
            import redis.asyncio as redis
            
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            client = await redis.from_url(redis_url)
            
            # Test ping
            await client.ping()
            
            # Test pub/sub
            await client.publish("health_check", "test")
            
            await client.close()
            self.log("  ✅", f"Redis connected: {redis_url}")
            return True
            
        except Exception as e:
            self.failures.append(f"Redis connection failed: {e}")
            self.log("  ❌", f"Redis error: {e}")
            return False
    
    async def check_timescale_connection(self) -> bool:
        """Test TimescaleDB connectivity"""
        self.log("🔍", "Checking TimescaleDB Connection...")
        
        try:
            import asyncpg
            
            conn = await asyncpg.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "password"),
                database=os.getenv("DB_NAME", "stockval"),
            )
            
            # Test query
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            
            self.log("  ✅", f"TimescaleDB connected")
            return True
            
        except Exception as e:
            self.failures.append(f"TimescaleDB connection failed: {e}")
            self.log("  ❌", f"TimescaleDB error: {e}")
            return False
    
    async def check_docker_containers(self) -> bool:
        """Check Docker container status"""
        self.log("🔍", "Checking Docker Containers...")
        
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=kis-service", "--filter", "name=kiwoom-service", 
                 "--filter", "name=recovery-worker", "--format", "{{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            containers = result.stdout.strip().split("\n")
            
            if not containers or containers == ['']:
                self.warnings.append("No collector containers running (may be in 'collection' profile)")
                self.log("  ⚠️ ", "No containers found (check docker-compose profile)")
                return True  # Not critical in development
            
            for container in containers:
                if container:
                    name, status = container.split("\t", 1)
                    if "Up" in status:
                        self.log("  ✅", f"{name}: {status}")
                    else:
                        self.failures.append(f"Container {name} not running: {status}")
                        self.log("  ❌", f"{name}: {status}")
                        
            return len(self.failures) == 0
            
        except subprocess.CalledProcessError as e:
            self.warnings.append(f"Docker check failed: {e}")
            self.log("  ⚠️ ", "Docker not accessible (OK in dev environment)")
            return True  # Not critical failure
    
    async def check_disk_space(self) -> bool:
        """Check available disk space"""
        self.log("🔍", "Checking Disk Space...")
        
        try:
            import shutil
            
            total, used, free = shutil.disk_usage("/")
            
            free_gb = free // (2**30)
            total_gb = total // (2**30)
            percent_free = (free / total) * 100
            
            if free_gb < 5:
                self.failures.append(f"Low disk space: {free_gb}GB free")
                self.log("  ❌", f"Only {free_gb}GB free (need at least 5GB)")
                return False
            elif free_gb < 10:
                self.warnings.append(f"Disk space running low: {free_gb}GB free")
                self.log("  ⚠️ ", f"{free_gb}GB / {total_gb}GB free ({percent_free:.1f}%)")
            else:
                self.log("  ✅", f"{free_gb}GB / {total_gb}GB free ({percent_free:.1f}%)")
                
            return True
            
        except Exception as e:
            self.warnings.append(f"Disk space check failed: {e}")
            return True  # Not critical
    
    async def check_critical_files(self) -> bool:
        """Verify critical files exist"""
        self.log("🔍", "Checking Critical Files...")
        
        critical_files = [
            "src/core/config.py",
            "src/data_ingestion/price/kr/kiwoom_ws.py",
            "src/data_ingestion/price/common/websocket_dual.py",
            "deploy/docker-compose.yml",
            ".env.prod",
        ]
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                self.log("  ✅", file_path)
            else:
                self.failures.append(f"Missing file: {file_path}")
                self.log("  ❌", file_path)
                
        return len(self.failures) == 0
    
    async def run_all_checks(self) -> bool:
        """Run all health checks"""
        self.log("🚀", "=" * 60)
        self.log("🚀", f"PRE-FLIGHT HEALTH CHECK - {datetime.now()}")
        self.log("🚀", "=" * 60)
        
        checks = [
            self.check_critical_files(),
            self.check_python_imports(),
            self.check_redis_connection(),
            self.check_timescale_connection(),
            self.check_docker_containers(),
            self.check_disk_space(),
        ]
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        # Summary
        self.log("", "=" * 60)
        passed = sum(1 for r in results if r is True)
        total = len(checks)
        
        if self.failures:
            self.log("❌", f"CRITICAL FAILURES ({len(self.failures)}):")
            for failure in self.failures:
                self.log("  ", f"- {failure}")
                
        if self.warnings:
            self.log("⚠️ ", f"WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                self.log("  ", f"- {warning}")
        
        if not self.failures:
            self.log("✅", f"ALL CRITICAL CHECKS PASSED ({passed}/{total})")
            return True
        else:
            self.log("❌", f"PREFLIGHT FAILED - {len(self.failures)} critical issue(s)")
            return False


async def main():
    """Main entry point"""
    checker = HealthCheck()
    success = await checker.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

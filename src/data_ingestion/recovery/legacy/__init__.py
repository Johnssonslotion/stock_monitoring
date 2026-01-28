"""
Legacy Recovery Modules (Deprecated)

ISSUE-044: 2026-01-28
- BackfillManager, merge_worker, RecoveryOrchestrator moved to legacy
- Superseded by: RealtimeVerifier + VerificationConsumer

See: docs/issues/ISSUE-044.md
"""

# Expose legacy modules for backward compatibility (if needed)
from .backfill_manager import BackfillManager
from .merge_worker import merge_recovery_data
from .recovery_orchestrator import RecoveryOrchestrator

__all__ = ['BackfillManager', 'merge_recovery_data', 'RecoveryOrchestrator']

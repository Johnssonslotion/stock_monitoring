
import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class SecurityManager:
    """
    Enforces security policies for sensitive data access and environment compliance.
    Implementation of RFC-006: Security & Governance Compliance.
    """
    SENSITIVE_KEYS: List[str] = ["KIS_APP_KEY", "KIS_APP_SECRET", "API_AUTH_SECRET"]

    @staticmethod
    def get_limit_sensitive(key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Securely retrieve a sensitive environment variable.
        This provides a hook point for future auditing or obfuscation logic.
        """
        val = os.getenv(key, default)
        return val
    
    @staticmethod
    def check_producer_env(strict: bool = True):
        """
        Verifies that we are in a 'Producer' environment (e.g., Real Collector).
        Producer MUST have API Keys to function.
        """
        missing = [k for k in ["KIS_APP_KEY", "KIS_APP_SECRET"] if not os.getenv(k)]
        if missing:
            msg = f"Critical Security: {missing} missing in Producer Environment! (.env.prod issue?)"
            if strict:
                raise EnvironmentError(msg)
            else:
                logger.error(msg)

    @staticmethod
    def check_consumer_env(strict: bool = False):
        """
        Verifies that we are in a 'Consumer' environment (e.g., Backtest Engine).
        Consumer SHOULD NOT have API Keys to ensure 'Physical Isolation'.
        """
        present = [k for k in ["KIS_APP_KEY", "KIS_APP_SECRET"] if os.getenv(k)]
        if present:
            msg = f"Security Breach: API Keys {present} found in Consumer Environment! This breaks Single-Key Governance."
            logger.warning(msg)
            if strict:
                raise EnvironmentError(msg)

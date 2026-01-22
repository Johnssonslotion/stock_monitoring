#!/usr/bin/env python3
"""
Environment Variable Validation Script (RFC-003 Enhancement)

Validates that all required environment variables are present before
container startup or application execution.

Usage:
    python scripts/validate_env.py --env-file .env.dev
    python scripts/validate_env.py --env-file .env.prod
"""

import os
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any


def load_schema(schema_path: str = ".env.schema.yaml") -> Dict[str, Any]:
    """Load environment variable schema from YAML file."""
    if not os.path.exists(schema_path):
        print(f"❌ Schema file not found: {schema_path}")
        sys.exit(1)
    
    with open(schema_path, 'r') as f:
        return yaml.safe_load(f)


def load_env_file(env_file: str) -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    
    if not os.path.exists(env_file):
        print(f"❌ Environment file not found: {env_file}")
        sys.exit(1)
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def validate_env(schema_path: str = ".env.schema.yaml", env_file: str = ".env") -> bool:
    """
    Validate environment variables against schema.
    
    Returns:
        bool: True if validation passes, False otherwise
    """
    schema = load_schema(schema_path)
    env_vars = load_env_file(env_file)
    
    # Also check OS environment variables (they override .env file)
    for key in schema.get('required', []):
        if key in os.environ:
            env_vars[key] = os.environ[key]
    
    missing = []
    empty = []
    
    # Check required variables
    for var in schema.get('required', []):
        if var not in env_vars:
            missing.append(var)
        elif not env_vars[var] or env_vars[var] == f"YOUR_{var}_HERE":
            empty.append(var)
    
    # Report results
    if missing or empty:
        print(f"\n❌ Environment validation FAILED for: {env_file}\n")
        
        if missing:
            print("Missing required variables:")
            for var in missing:
                print(f"  - {var}")
        
        if empty:
            print("\nEmpty or placeholder values:")
            for var in empty:
                print(f"  - {var} (value: '{env_vars.get(var, '')}')")
        
        print(f"\nPlease update {env_file} or set these as environment variables.\n")
        return False
    else:
        print(f"✅ All required environment variables present in {env_file}")
        
        # Show optional variables status
        optional_set = []
        for var in schema.get('optional', []):
            if var in env_vars and env_vars[var]:
                optional_set.append(var)
        
        if optional_set:
            print(f"   Optional variables set: {', '.join(optional_set)}")
        
        return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate environment variables')
    parser.add_argument('--env-file', default='.env', help='Path to .env file')
    parser.add_argument('--schema', default='.env.schema.yaml', help='Path to schema YAML')
    
    args = parser.parse_args()
    
    success = validate_env(schema_path=args.schema, env_file=args.env_file)
    sys.exit(0 if success else 1)

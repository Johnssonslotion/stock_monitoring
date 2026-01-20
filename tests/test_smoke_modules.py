import importlib
import pkgutil
import sys
import os
import logging
from pathlib import Path
import pytest

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_modules(package_path):
    """
    Recursively find all modules in a package directory.
    Yields full module names (e.g., 'src.data_ingestion.ticks')
    """
    package_name = os.path.basename(package_path)
    if package_name == 'src':
        base_prefix = 'src.'
    else:
        # Assuming we are looking inside src primarily
        base_prefix = f'src.{package_name}.'

    # Exclude directories
    EXCLUDE_DIRS = ['node_modules', '__pycache__', 'venv', '.venv']
    EXCLUDE_FILES = ['unified_collector.py', 'app.py'] # Deprecated or missing deps (dash)

    for root, dirs, files in os.walk(package_path):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file.endswith(".py") and file != "__init__.py" and file not in EXCLUDE_FILES:
                # Construct module path
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                module_name = rel_path.replace(os.sep, ".")[:-3]  # Strip .py
                yield module_name

def get_all_modules():
    """Helper to get list of all modules in src"""
    src_path = os.path.join(PROJECT_ROOT, "src")
    return list(find_modules(src_path))

# Parametrize the test with all discovered modules
@pytest.mark.parametrize("module_name", get_all_modules())
def test_module_importable(module_name):
    """
    Smoke Test: Verify that every module in src/ can be imported.
    This catches SyntaxErrors, IndentationErrors, and immediate ImportErrors.
    """
    try:
        importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(f"Failed to import module '{module_name}': {e}")

if __name__ == "__main__":
    # Allow running directly for quick check
    sys.exit(pytest.main(["-v", __file__]))

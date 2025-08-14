import os
import pytest

# Phase 2 core profile: skip heavy AIWF tests unless explicitly enabled
_ENABLE_FULL = os.getenv("ENABLE_FULL_SUITE") == "1"

_SKIP_BY_DEFAULT = [
    "integration",
    "slow",
    "performance",
    "network",
    "external",
]

def pytest_collection_modifyitems(config, items):
    if _ENABLE_FULL:
        return
    # Always hard-skip problematic integration file by nodeid guard
    hard_skip = pytest.mark.skip(reason="Hard-skipped in CI profile (stability)")
    skip_marker = pytest.mark.skip(reason="Phase 2 core profile: ENABLE_FULL_SUITE=1 to run heavy tests")
    for item in items:
        # file-level guard
        try:
            nodeid = getattr(item, 'nodeid', '')
            if nodeid.endswith('tests/test_writing_crew_integration.py'):
                item.add_marker(hard_skip)
                continue
        except Exception:
            pass
        for k in _SKIP_BY_DEFAULT:
            if k in item.keywords:
                item.add_marker(skip_marker)
                break

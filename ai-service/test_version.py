#!/usr/bin/env python3
import sys
sys.path.insert(0, 'setup')
from setup_ollama import parse_version, compare_versions

# Test various version strings
test_versions = [
    ('ollama version 0.1.20', '0.1.27'),  # Older version
    ('ollama version v0.1.27', '0.1.27'), # Same version with 'v' prefix
    ('ollama version 0.1.30', '0.1.27')   # Newer version
]

# Run tests
for version_str, target in test_versions:
    parsed = parse_version(version_str)
    result, msg = compare_versions(parsed, target)
    print(f'Version: {version_str}')
    print(f'Parsed: {parsed}')
    print(f'Target: {target}')
    print(f'Needs update? {result}')
    print(f'Reason: {msg}')
    print('-' * 50)

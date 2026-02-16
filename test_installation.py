#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify all dependencies are installed correctly.
Run this before starting the application.
"""

import sys

print("=" * 80)
print("Bad Respondents Detector v2.0 - Dependency Check")
print("=" * 80)
print()

errors = []
warnings = []

# Test Python version
print("✓ Checking Python version...")
if sys.version_info < (3, 8):
    errors.append(f"Python 3.8+ required, you have {sys.version}")
else:
    print(f"  → Python {sys.version.split()[0]} ✓")

# Test required modules
required_modules = [
    ('flask', 'Flask'),
    ('flask_cors', 'Flask-CORS'),
    ('pyreadstat', 'pyreadstat'),
    ('pandas', 'pandas'),
    ('numpy', 'numpy'),
    ('docx', 'python-docx'),
]

optional_modules = [
    ('mammoth', 'mammoth'),
]

print("\n✓ Checking required modules...")
for module_name, package_name in required_modules:
    try:
        __import__(module_name)
        print(f"  → {package_name} ✓")
    except ImportError:
        errors.append(f"Missing required module: {package_name}")
        print(f"  ✗ {package_name} MISSING")

print("\n✓ Checking optional modules...")
for module_name, package_name in optional_modules:
    try:
        __import__(module_name)
        print(f"  → {package_name} ✓")
    except ImportError:
        warnings.append(f"Optional module {package_name} not installed (recommended)")
        print(f"  ! {package_name} not installed (optional)")

# Test main application modules
print("\n✓ Checking application modules...")
try:
    from bad_respondents_detector import analyze_with_questionnaire
    print("  → bad_respondents_detector.py ✓")
except Exception as e:
    errors.append(f"Cannot import bad_respondents_detector: {e}")
    print(f"  ✗ bad_respondents_detector.py FAILED")

try:
    from questionnaire_parser import parse_questionnaire
    print("  → questionnaire_parser.py ✓")
except Exception as e:
    errors.append(f"Cannot import questionnaire_parser: {e}")
    print(f"  ✗ questionnaire_parser.py FAILED")

try:
    from spss_syntax_unified import generate_spss_syntax_unified
    print("  → spss_syntax_unified.py ✓")
except Exception as e:
    errors.append(f"Cannot import spss_syntax_unified: {e}")
    print(f"  ✗ spss_syntax_unified.py FAILED")

# Test file structure
print("\n✓ Checking file structure...")
import os

required_files = [
    'app.py',
    'bad_respondents_detector.py',
    'questionnaire_parser.py',
    'spss_syntax_unified.py',
    'static/index.html',
    'requirements.txt',
]

for filepath in required_files:
    if os.path.exists(filepath):
        print(f"  → {filepath} ✓")
    else:
        errors.append(f"Missing required file: {filepath}")
        print(f"  ✗ {filepath} MISSING")

# Summary
print("\n" + "=" * 80)
if errors:
    print("❌ ERRORS FOUND:")
    for error in errors:
        print(f"  • {error}")
    print("\nPlease fix these errors before starting the application.")
    print("\nTo install missing modules:")
    print("  pip install -r requirements.txt")
elif warnings:
    print("⚠️  WARNINGS:")
    for warning in warnings:
        print(f"  • {warning}")
    print("\n✅ Application should work, but consider installing optional modules.")
    print("\nTo install recommended modules:")
    print("  pip install mammoth")
else:
    print("✅ ALL CHECKS PASSED!")
    print("\nYou can now start the application:")
    print("  python app.py")
    print("\nThen open your browser:")
    print("  http://localhost:5000")

print("=" * 80)

sys.exit(0 if not errors else 1)

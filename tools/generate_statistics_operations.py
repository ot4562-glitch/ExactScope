#!/usr/bin/env python3
"""Compatibility entry point for the canonical Statistics metadata generator.

Use tools/generate_statistics_metadata.py; no second binding manifest is maintained.
"""
from generate_statistics_metadata import main

if __name__ == "__main__":
    raise SystemExit(main())

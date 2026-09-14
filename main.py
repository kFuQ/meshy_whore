#!/usr/bin/env python3
"""Meshy Studio launcher.

Run with:  python main.py   (or)   python -m meshy_studio
"""
from __future__ import annotations

import sys

from meshy_studio import run

if __name__ == "__main__":
    sys.exit(run())

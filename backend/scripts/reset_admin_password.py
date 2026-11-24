#!/usr/bin/env python3
"""
Sentinel SOC — Secure Administrator Password Reset & Recovery CLI Tool
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.reset_admin_password import main

if __name__ == "__main__":
    main()

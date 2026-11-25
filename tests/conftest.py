"""Shared test setup.

Real SuperFaktura credentials must never reach a test. The developer shell may
export SUPERFAKTURA_EMAIL / SUPERFAKTURA_API_KEY for a production account, so
they are removed here before server.py is imported. Only the sandbox suite
(tests/test_sandbox.py) talks to an API, and only with SUPERFAKTURA_SANDBOX_*.
"""

import os
import sys
from pathlib import Path

REAL_VARS = (
    "SUPERFAKTURA_EMAIL",
    "SUPERFAKTURA_API_KEY",
    "SUPERFAKTURA_COMPANY_ID",
    "SUPERFAKTURA_COUNTRY",
    "SUPERFAKTURA_API_URL",
)
for name in REAL_VARS:
    os.environ.pop(name, None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#!/usr/bin/env python3
"""Camoufox remote server launcher for Docker."""

import subprocess
import base64
import os
import orjson
from pathlib import Path

from camoufox.utils import launch_options
from camoufox.server import LAUNCH_SCRIPT, get_nodejs


def to_camel_case(s):
    parts = s.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])


def clean_dict(d):
    """Convert to camelCase and strip None values (fixes Playwright 'expected object, got null')."""
    if isinstance(d, dict):
        return {to_camel_case(k): clean_dict(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [clean_dict(i) for i in d]
    return d


print("Launching Camoufox server...", flush=True)

config = launch_options(
    headless=True,
    humanize=True,
    port=9222,
    ws_path="browser",
)

config_clean = clean_dict(config)
data = orjson.dumps(config_clean)

nodejs = get_nodejs()
print(f"Node: {nodejs}", flush=True)
print(f"Script: {LAUNCH_SCRIPT}", flush=True)

# cwd must point to Playwright's driver package (contains lib/browserServerImpl.js)
pw_package = Path(nodejs).parent / "package"
process = subprocess.Popen(
    [nodejs, str(LAUNCH_SCRIPT)],
    cwd=str(pw_package),
    stdin=subprocess.PIPE,
    text=True,
)

if process.stdin:
    process.stdin.write(base64.b64encode(data).decode())
    process.stdin.close()

process.wait()

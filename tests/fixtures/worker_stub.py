"""Controlled subprocess used by the worker lifecycle integration tests."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


message = json.loads(sys.stdin.readline())
mode = message.get("mode", "result")

if mode == "result":
    print(json.dumps({"event": "result", "value": {"operation": message["operation"]}}), flush=True)
elif mode == "environment":
    print(
        json.dumps(
            {
                "event": "result",
                "value": {
                    "token": os.environ.get("TELEGRAM_BOT_TOKEN"),
                    "user": os.environ.get("OPENMEDIA_USER_ID"),
                    "keys": sorted(os.environ),
                },
            }
        ),
        flush=True,
    )
elif mode == "malformed":
    print("not-json", flush=True)
elif mode == "multiple":
    print(json.dumps({"event": "result", "value": 1}), flush=True)
    print(json.dumps({"event": "error", "category": "internal"}), flush=True)
elif mode == "oversized":
    print(json.dumps({"event": "result", "value": "x" * (2 * 1024 * 1024)}), flush=True)
elif mode == "stderr":
    sys.stderr.write("x" * (300 * 1024))
    print(json.dumps({"event": "result", "value": True}), flush=True)
elif mode == "sensitive_stderr":
    sys.stderr.write(
        "download failed for https://cdn.example.invalid/media.mp4?token=signed-secret "
        "TELEGRAM_BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyzABCDE"
    )
    print(json.dumps({"event": "result", "value": True}), flush=True)
elif mode == "progress":
    for index in range(100):
        print(json.dumps({"event": "progress", "stage": "download", "bytes": index}), flush=True)
    print(json.dumps({"event": "result", "value": True}), flush=True)
elif mode == "rate":
    print(
        json.dumps(
            {"event": "rate_request", "platform": "instagram", "request_class": "metadata"}
        ),
        flush=True,
    )
    reply = json.loads(sys.stdin.readline())
    print(json.dumps({"event": "rate_limited", "platform": "instagram", "retry_after": 2}), flush=True)
    print(json.dumps({"event": "result", "value": reply}), flush=True)
elif mode == "hang":
    marker = Path(message["marker"])
    time.sleep(2)
    marker.write_text("worker survived", encoding="utf-8")
else:
    print(json.dumps({"event": "error", "category": "internal"}), flush=True)

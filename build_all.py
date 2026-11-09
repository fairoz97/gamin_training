#!/usr/bin/env python3
"""Rebuild every dashboard from data/garmin.json.

    python build_all.py                       # uses config.json if present
    python build_all.py --race 2027-03-14 --race-name "My Race" --first-name Fai

config.json (optional, copy config.example.json) holds your defaults; flags override it.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    cfg = {}
    cp = HERE / "config.json"
    if cp.exists():
        cfg = json.loads(cp.read_text())
    for key, env in (("race", "RACE_DATE"), ("race_name", "RACE_NAME"), ("race_time", "RACE_TIME"), ("first_name", "FIRST_NAME")):
        if os.environ.get(env):
            cfg[key] = os.environ[env]

    ap = argparse.ArgumentParser()
    ap.add_argument("--data")
    ap.add_argument("--race", default=cfg.get("race"))
    ap.add_argument("--race-name", default=cfg.get("race_name"))
    ap.add_argument("--race-time", default=cfg.get("race_time"))
    ap.add_argument("--first-name", default=cfg.get("first_name"))
    a = ap.parse_args()

    def flags(*names):
        out = []
        for n in names:
            v = getattr(a, n)
            if v:
                out += ["--" + n.replace("_", "-"), v]
        return out

    data = ["--data", a.data] if a.data else []
    jobs = [
        ("build_commander.py", data + flags("race", "race_name")),
        ("build_coach.py", data + flags("race", "race_name", "first_name")),
        ("build_tinkerer.py", data),
        ("build_brain.py", data + flags("race", "race_name", "race_time")),
    ]
    failed = 0
    for script, args in jobs:
        p = subprocess.run([sys.executable, script] + args, cwd=HERE, capture_output=True, text=True)
        print((p.stdout or p.stderr).strip().splitlines()[-1] if (p.stdout or p.stderr).strip() else script)
        if p.returncode:
            failed += 1
            print(p.stderr.strip(), file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

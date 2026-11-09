#!/usr/bin/env python3
"""Build a double-click-able brain.html from data/garmin.json.

    python build_brain.py --race 2027-03-14 --race-name "My Race" --race-time 06:00
"""
import argparse
import json
from pathlib import Path

from build_commander import build
from widget import inject

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "data" / "garmin.json"))
    ap.add_argument("--out", default=str(HERE / "brain.html"))
    ap.add_argument("--race", help="goal race date, YYYY-MM-DD")
    ap.add_argument("--race-name")
    ap.add_argument("--race-time", default="06:00", help="start time HH:MM, Singapore time (default 06:00)")
    a = ap.parse_args()

    raw = json.loads(Path(a.data).read_text())
    d = build(raw, a.race, a.race_name)
    if d["race"]["date"]:
        d["race"]["time"] = a.race_time

    payload = json.dumps(d, separators=(",", ":")).replace("</", "<\\/")
    tpl = (HERE / "brain.template.html").read_text()
    Path(a.out).write_text(inject(tpl.replace("/*__DATA__*/null", payload)))
    print(f"Wrote {a.out} ({Path(a.out).stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a double-click-able tinkerer.html (run explorer) from data/garmin.json.

    python build_tinkerer.py
"""
import argparse
import json
from pathlib import Path

from widget import inject

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "data" / "garmin.json"))
    ap.add_argument("--out", default=str(HERE / "tinkerer.html"))
    a = ap.parse_args()

    raw = json.loads(Path(a.data).read_text())
    runs = []
    for r in raw.get("activities", []):
        at = r.get("activityType")
        key = at.get("typeKey") if isinstance(at, dict) else at
        if "run" not in (key or "") or not r.get("distance") or not r.get("duration"):
            continue
        zones = [r.get(f"hrTimeInZone_{i}") for i in range(1, 6)]
        runs.append({
            "id": r["activityId"],
            "name": r.get("activityName"),
            "type": key,
            "start": r["startTimeLocal"],
            "date": r["startTimeLocal"][:10],
            "dist": r["distance"],
            "dur": r["duration"],
            "hr": r.get("averageHR"),
            "te": r.get("trainingEffectLabel"),
            "ate": r.get("aerobicTrainingEffect"),
            "z": zones if any(z is not None for z in zones) else None,
        })
    runs.sort(key=lambda x: x["start"])

    payload = json.dumps({"fetched": raw.get("fetched_at"), "runs": runs}, separators=(",", ":")).replace("</", "<\\/")
    tpl = (HERE / "tinkerer.template.html").read_text()
    Path(a.out).write_text(inject(tpl.replace("/*__DATA__*/null", payload)))
    print(f"Wrote {a.out}: {len(runs)} runs ({Path(a.out).stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()

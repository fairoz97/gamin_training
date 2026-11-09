#!/usr/bin/env python3
"""Build a double-click-able coach.html from data/garmin.json.

    python build_coach.py --race 2027-03-14 --race-name "My Race" --first-name Fai
"""
import argparse
import json
from pathlib import Path

from build_commander import build

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "data" / "garmin.json"))
    ap.add_argument("--out", default=str(HERE / "coach.html"))
    ap.add_argument("--race", help="goal race date, YYYY-MM-DD")
    ap.add_argument("--race-name")
    ap.add_argument("--name", help="athlete full name (default: from the Garmin profile)")
    ap.add_argument("--first-name", help="name used in the drafted note (default: first word of the name)")
    a = ap.parse_args()

    raw = json.loads(Path(a.data).read_text())
    d = build(raw, a.race, a.race_name)

    by_id = {x["activityId"]: x for x in raw.get("activities", [])}
    for act in d["activities"]:
        r = by_id[act["id"]]
        zones = [r.get(f"hrTimeInZone_{i}") for i in range(1, 6)]
        act["z"] = zones if any(z is not None for z in zones) else None
        act["te"] = r.get("trainingEffectLabel")
        act["ate"] = r.get("aerobicTrainingEffect")
        act["hr"] = r.get("averageHR")

    owner = next((x.get("ownerFullName") for x in raw.get("activities", []) if x.get("ownerFullName")), "Athlete")
    name = a.name or " ".join(w.capitalize() for w in owner.split())
    d["athlete"] = {"name": name, "first": a.first_name or name.split()[0]}

    payload = json.dumps(d, separators=(",", ":")).replace("</", "<\\/")
    tpl = (HERE / "coach.template.html").read_text()
    Path(a.out).write_text(tpl.replace("/*__DATA__*/null", payload))
    print(f"Wrote {a.out} ({Path(a.out).stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()

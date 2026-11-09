#!/usr/bin/env python3
"""Build a double-click-able commander.html from data/garmin.json.

    python build_commander.py                       # uses data/garmin.json
    python build_commander.py --race 2027-03-14 --race-name "Singapore Marathon"
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SGT = timezone(timedelta(hours=8))


def num(v):
    return v if isinstance(v, (int, float)) else None


def build(raw, race_date, race_name):
    fetched = datetime.fromisoformat(raw["fetched_at"])
    today = fetched.astimezone(SGT).date().isoformat()

    activities = []
    for a in raw.get("activities", []):
        at = a.get("activityType")
        activities.append({
            "id": a["activityId"],
            "name": a.get("activityName"),
            "type": at.get("typeKey") if isinstance(at, dict) else at,
            "start": a["startTimeLocal"],
            "date": a["startTimeLocal"][:10],
            "dist": a.get("distance") or 0,
            "dur": a.get("duration") or 0,
            "load": num(a.get("activityTrainingLoad")),
            "hr": num(a.get("averageHR")),
        })

    daily = {}
    for chunk in raw.get("daily_summaries", []):
        data = chunk.get("data")
        for r in (data.get("data") if isinstance(data, dict) else data) or []:
            bb = r.get("bodyBattery") or {}
            st = r.get("stress") or {}
            daily[r["calendarDate"]] = {
                "d": r["calendarDate"],
                "rhr": (r.get("heartRate") or {}).get("restingValue"),
                "stress": st.get("avgLevel"), "stressMax": st.get("maxLevel"),
                "bbLatest": bb.get("latestValue"), "bbMax": bb.get("maxValue"), "bbMin": bb.get("minValue"),
            }

    sleep, need = {}, None
    for chunk in raw.get("sleep", []) + raw.get("last_night_sleep", []):
        for r in chunk.get("data") or []:
            if not r.get("sleepTimeSeconds") or not r.get("calendarDate"):
                continue
            sleep[r["calendarDate"]] = {
                "d": r["calendarDate"], "secs": r["sleepTimeSeconds"],
                "hrs": round(r["sleepTimeSeconds"] / 3600, 2),
                "score": ((r.get("sleepScores") or {}).get("overall") or {}).get("value"),
            }
            need = (r.get("sleepNeed") or {}).get("baseline") or need

    hrv = {}
    for chunk in raw.get("hrv", []) + raw.get("last_night_hrv", []):
        data = chunk.get("data")
        for h in (data.get("hrvSummaries") if isinstance(data, dict) else None) or []:
            b = h.get("baseline") or {}
            hrv[h["calendarDate"]] = {
                "d": h["calendarDate"], "weekly": h.get("weeklyAvg"), "last": h.get("lastNightAvg"),
                "status": h.get("status"), "balLow": b.get("balancedLow"), "balHigh": b.get("balancedUpper"),
            }

    hr = raw.get("today_heart_rate") or {}
    return {
        "fetched": raw["fetched_at"], "today": today,
        "race": {"name": race_name, "date": race_date},
        "activities": activities,
        "daily": sorted(daily.values(), key=lambda r: r["d"]),
        "sleep": sorted(sleep.values(), key=lambda r: r["d"]),
        "sleepNeedMin": need or 480,
        "hrv": sorted(hrv.values(), key=lambda r: r["d"]),
        "hr": {"rhr": hr.get("restingHeartRate"), "avg7": hr.get("lastSevenDaysAvgRestingHeartRate"),
               "min": hr.get("minHeartRate"), "max": hr.get("maxHeartRate")},
        "fitnessAge": raw.get("fitness_age"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "data" / "garmin.json"))
    ap.add_argument("--out", default=str(HERE / "commander.html"))
    ap.add_argument("--race", help="goal race date, YYYY-MM-DD")
    ap.add_argument("--race-name", help="goal race name")
    a = ap.parse_args()

    raw = json.loads(Path(a.data).read_text())
    payload = json.dumps(build(raw, a.race, a.race_name), separators=(",", ":")).replace("</", "<\\/")
    tpl = (HERE / "commander.template.html").read_text()
    Path(a.out).write_text(tpl.replace("/*__DATA__*/null", payload))
    print(f"Wrote {a.out} ({Path(a.out).stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()

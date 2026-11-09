#!/usr/bin/env python3
"""Pull Garmin Personal API data into data/garmin.json."""
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = "https://personal.connectapi.garmin.com"
TOKEN_URL = BASE + "/personalapitoken-service/personal-api/personal-api-key/token"
MAX_BYTES = 250_000          # stay under Garmin's ~256 KB response limit
PAGE_SIZE = 20
MAX_RETRIES = 6
POLITE_DELAY = 0.2


def load_env(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Garmin:
    def __init__(self, api_key):
        self.api_key = api_key
        self.s = requests.Session()
        self.token = None

    def refresh_token(self):
        r = self._send("POST", TOKEN_URL, headers={"Authorization": f"ApiKey {self.api_key}"})
        r.raise_for_status()
        self.token = r.text.strip().strip('"')  # bare string, not JSON
        if not self.token:
            raise RuntimeError("Empty token returned")

    def _send(self, method, url, **kw):
        for attempt in range(MAX_RETRIES):
            r = self.s.request(method, url, timeout=60, **kw)
            if r.status_code != 429:
                return r
            wait = r.headers.get("Retry-After")
            wait = float(wait) if wait and wait.replace(".", "").isdigit() else 2 ** attempt
            print(f"  429 on {url.split('?')[0]}; sleeping {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
        return r

    def get(self, path, params=None):
        """GET with Bearer token; refreshes once on 401. Returns the Response."""
        if self.token is None:
            self.refresh_token()
        url = BASE + path
        for auth_try in range(2):
            r = self._send("GET", url, params=params,
                           headers={"Authorization": f"Bearer {self.token}"})
            if r.status_code == 401 and auth_try == 0:
                self.refresh_token()
                continue
            break
        time.sleep(POLITE_DELAY)
        return r


def d(x):
    return x.isoformat()


def fetch_range(g, make_path, make_params, start, end):
    """Fetch [start, end]; if the response is too large, split the range in half."""
    r = g.get(make_path(start, end), make_params(start, end))
    too_big = r.status_code == 413 or len(r.content) > MAX_BYTES
    if too_big and end > start:
        mid = start + (end - start) // 2
        return (fetch_range(g, make_path, make_params, start, mid)
                + fetch_range(g, make_path, make_params, mid + timedelta(days=1), end))
    r.raise_for_status()
    data = r.json() if r.content.strip() else None  # some ranges return an empty body
    return [{"start": d(start), "end": d(end), "data": data}]


def chunked(g, make_path, make_params, start, end, days):
    out, cur = [], start
    while cur <= end:
        stop = min(cur + timedelta(days=days - 1), end)
        out += fetch_range(g, make_path, make_params, cur, stop)
        cur = stop + timedelta(days=1)
    return out


def records(payload):
    """Best-effort: the list of records inside a response."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        lists = [v for v in payload.values() if isinstance(v, list)]
        return max(lists, key=len) if lists else []
    return []


def safe(errors, name, fn):
    try:
        return fn()
    except Exception as e:  # keep going; record what failed
        errors[name] = f"{type(e).__name__}: {e}"
        print(f"  ! {name} failed: {e}", file=sys.stderr)
        return None


def main():
    load_env()
    key = os.environ.get("GARMIN_PERSONAL_API_KEY", "").strip()
    if not key:
        sys.exit("GARMIN_PERSONAL_API_KEY is empty. Put it in .env first.")

    g = Garmin(key)
    g.refresh_token()
    print("Got token.")

    today = date.today()
    yesterday = today - timedelta(days=1)
    errors = {}
    out = {"fetched_at": datetime.now(timezone.utc).isoformat()}

    # Activities: 20 per page until empty
    def get_activities():
        acts, start = [], 0
        while True:
            r = g.get("/activitylist-service/activities/search/activities",
                      {"start": start, "limit": PAGE_SIZE})
            r.raise_for_status()
            page = r.json()
            if not page:
                break
            acts += page
            start += PAGE_SIZE
            if start % 200 == 0:
                print(f"  {len(acts)} activities so far...")
        return acts
    print("Activities...")
    out["activities"] = safe(errors, "activities", get_activities) or []

    ds = lambda a, b: {"startDate": d(a), "endDate": d(b)}

    print("Daily summaries (365 d)...")
    out["daily_summaries"] = safe(errors, "daily_summaries", lambda: chunked(
        g, lambda a, b: "/usersummary-service/v2/dailysummaries", ds,
        today - timedelta(days=364), today, 60)) or []

    print("Sleep (365 nights)...")
    out["sleep"] = safe(errors, "sleep", lambda: chunked(
        g, lambda a, b: "/sleep-service/sleep/dailySleepSummariesByDate", ds,
        today - timedelta(days=364), today, 31)) or []

    print("HRV (1 year)...")
    out["hrv"] = safe(errors, "hrv", lambda: chunked(
        g, lambda a, b: f"/hrv-service/hrv/daily/{d(a)}/{d(b)}", lambda a, b: None,
        today - timedelta(days=364), today, 31)) or []

    print("Body Battery (90 d)...")
    out["body_battery"] = safe(errors, "body_battery", lambda: chunked(
        g, lambda a, b: "/wellness-service/wellness/bodyBattery/reports/daily", ds,
        today - timedelta(days=89), today, 31)) or []

    print("Today / last night / profile...")
    # Last night's sleep + HRV reuse the documented range endpoints (yesterday..today).
    out["last_night_sleep"] = safe(errors, "last_night_sleep", lambda: fetch_range(
        g, lambda a, b: "/sleep-service/sleep/dailySleepSummariesByDate", ds, yesterday, today))
    out["last_night_hrv"] = safe(errors, "last_night_hrv", lambda: fetch_range(
        g, lambda a, b: f"/hrv-service/hrv/daily/{d(a)}/{d(b)}", lambda a, b: None, yesterday, today))

    # NOTE: these three paths are not in the spec I was given; they follow Garmin Connect
    # conventions and may need adjusting for the Personal API.
    def simple(path, params=None):
        r = g.get(path, params)
        r.raise_for_status()
        return r.json()
    out["today_heart_rate"] = safe(errors, "today_heart_rate", lambda: simple(
        "/wellness-service/wellness/dailyHeartRate", {"date": d(today)}))
    out["heart_rate_zones"] = safe(errors, "heart_rate_zones", lambda: simple(
        "/biometric-service/heartRateZones"))
    out["fitness_age"] = safe(errors, "fitness_age", lambda: simple(
        f"/fitnessage-service/fitnessage/{d(today)}"))

    out["errors"] = errors

    Path("data").mkdir(exist_ok=True)
    Path("data/garmin.json").write_text(json.dumps(out, indent=2))

    nights = sum(len(records(c["data"])) for c in out["sleep"])
    print(f"\nActivities: {len(out['activities'])}")
    print(f"Sleep nights: {nights}")
    if errors:
        print("Errors:", json.dumps(errors, indent=2))
    print("Wrote data/garmin.json")


if __name__ == "__main__":
    main()

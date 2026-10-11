#!/usr/bin/env python3
"""
Fetch the daily contribution counts for one calendar year (the same view as the
profile's "N contributions in YYYY" panel) and write data/contributions.json.

Two sources, tried in this order:

1. GitHub GraphQL API, when CONTRIB_TOKEN is set (a personal access token with
   `read:user`, stored as a repository secret). It queries as the profile
   owner, so it sees the same numbers the owner sees, private activity included.
2. GitHub's public, unauthenticated contributions fragment (what any visitor
   sees: public activity, plus private counts only if the profile publishes them).

The JSON has no timestamp on purpose: the file only changes when the data does,
so the workflow only commits when there is something new.
Run by .github/workflows/update-skyline.yml.
"""
import datetime
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_PROFILE_USER", "Luisssantos56")
YEAR = int(os.environ.get("GH_PROFILE_YEAR") or datetime.datetime.now(datetime.timezone.utc).year)
TOKEN = os.environ.get("CONTRIB_TOKEN", "").strip()
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")
UA = {"User-Agent": "profile-readme-bot/1.0"}

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_graphql():
    resp = requests.post(
        "https://api.github.com/graphql",
        json={
            "query": QUERY,
            "variables": {
                "login": USERNAME,
                "from": f"{YEAR}-01-01T00:00:00Z",
                "to": f"{YEAR}-12-31T23:59:59Z",
            },
        },
        headers={**UA, "Authorization": f"bearer {TOKEN}"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [
        {"date": d["date"], "count": d["contributionCount"]}
        for w in cal["weeks"]
        for d in w["contributionDays"]
    ]
    days.sort(key=lambda d: d["date"])
    return days, cal["totalContributions"]


def fetch_public():
    url = f"https://github.com/users/{USERNAME}/contributions?from={YEAR}-01-01&to={YEAR}-12-31"
    resp = requests.get(url, headers=UA, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        sys.exit(1)

    days = []
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        td_id = td.get("id")
        tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else ""
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            m = re.match(r"(\d+)", text)
            count = int(m.group(1)) if m else 0
        days.append({"date": date, "count": count})
    days.sort(key=lambda d: d["date"])

    # the heading the profile shows: "879 contributions in 2026"
    m = re.search(r"([\d,]+)\s+contributions?\s+in\s+", soup.get_text(" ", strip=True))
    total = int(m.group(1).replace(",", "")) if m else None
    return days, total


if __name__ == "__main__":
    source = "public fragment"
    try:
        if TOKEN:
            days, total = fetch_graphql()
            source = "graphql (owner view)"
        else:
            days, total = fetch_public()
    except Exception as exc:  # token revoked/expired -> still publish the public view
        if not TOKEN:
            raise
        print(f"graphql failed ({exc}); falling back to the public fragment", file=sys.stderr)
        days, total = fetch_public()

    # keep only the requested year
    days = [d for d in days if d["date"].startswith(f"{YEAR}-")]
    summed = sum(d["count"] for d in days)
    if total is None:
        total = summed
    if total != summed:
        print(f"note: heading total {total} differs from sum of days {summed}", file=sys.stderr)

    data = {"username": USERNAME, "year": YEAR, "total": total, "days": days}
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {OUT_PATH} from {source}: {YEAR}, {len(days)} days, total {total}")

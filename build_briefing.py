#!/usr/bin/env python3
"""
Morning Briefing builder.

Re-derives briefing-data.js every run from Kramer's live KRAMOS files so the
auto-playing slideshow (index.html) shows fresh info each morning:

  - wins (yesterday + this week)  <-  priorities.md  "Recently Accomplished"
  - project status board          <-  project-timeline.json
  - two "what to work on" picks    <-  serendipity.json
  - today's calendar + 3 headlines <-  briefing-feed.json (the live external bits)

The local-file sections are fully autonomous, so this can be cron'd. The feed
file holds the parts that need a connected session (Cadence pulls the calendar,
Pax pulls headlines); if it's missing, those slides degrade gracefully.

Usage:  python3 build_briefing.py            # builds for today
        python3 build_briefing.py 2026-06-12 # builds as if it were this date
"""

import json, re, sys
from datetime import datetime, timedelta, date
from pathlib import Path

HERE = Path(__file__).resolve().parent

def _find_repo(start):
    """Walk up until we hit the repo root (the dir holding priorities.md / CLAUDE.md).
    Robust to symlinked 'coding projects' folders that confuse parents[]."""
    for d in [start, *start.parents]:
        if (d / "priorities.md").exists() and (d / "CLAUDE.md").exists():
            return d
    return start.parents[2]  # fallback to the documented layout

REPO = _find_repo(HERE)

PRIORITIES = REPO / "priorities.md"
ARCHIVE    = REPO / "pastWork" / "priorities-archive-2026.md"   # wins live here since the Oct 2026 split
TIMELINE   = REPO / "project-timeline.json"
SERENDIPITY= REPO / "serendipity.json"
FEED       = HERE / "briefing-feed.json"
OUT        = HERE / "briefing-data.js"
SCHEDULES  = REPO / "knowledge" / "Berklee Courses" / "course-schedules"

SEMESTER_RE = re.compile(r"\b(Spring|Summer|Fall|Winter)\s+(20\d{2})\b", re.IGNORECASE)


def is_term_over(name, today):
    """A project named after a semester (e.g. 'LHUM400 Summer 2026') is stale
    once that semester's own course-schedules end date has passed. Same signal
    the dashboard's 'term over, archive?' prompt uses, applied here so an
    unattended nightly build doesn't need a human to click it."""
    m = SEMESTER_RE.search(name)
    if not m:
        return False
    season, year = m.group(1).lower(), m.group(2)
    schedule_file = SCHEDULES / f"{season}-{year}.json"
    if not schedule_file.exists():
        return False
    try:
        data = json.loads(schedule_file.read_text(encoding="utf-8"))
        end = data.get("endDate")
        return bool(end) and date.fromisoformat(end) < today
    except (ValueError, json.JSONDecodeError):
        return False

MONTHS = {m: i for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], start=1)}


def parse_win_date(tag, year):
    """'Jun 12' -> date(2026,6,12), best-effort."""
    m = re.match(r"([A-Za-z]{3,9})\s+(\d{1,2})", tag.strip())
    if not m:
        return None
    mon = MONTHS.get(m.group(1)[:3].title())
    if not mon:
        return None
    try:
        return date(year, mon, int(m.group(2)))
    except ValueError:
        return None


def load_wins(today):
    """Parse the 'Recently Accomplished' bullets in priorities.md.

    Each line looks like:  - <text> -- Jun 12 (Team, Team)
    Returns (yesterday_list, week_list) of {text, team, date}.
    """
    # Wins moved to the archive's "## Accomplished" (newest first); the old
    # "Recently Accomplished" block in priorities.md is still read if present.
    block = []
    for src, head in ((ARCHIVE, "## accomplished"), (PRIORITIES, "## recently accomplished")):
        if not src.exists():
            continue
        grab = False
        for ln in src.read_text(encoding="utf-8").splitlines():
            t = ln.strip()
            if t.startswith("## ") or t.startswith("### "):
                grab = t.lower().startswith(head) and t.startswith("## ")
                continue
            if grab and t.startswith("- "):
                block.append(t[2:])

    wins = []
    for raw in block:
        # split off trailing date + team:  text -- Jun 12 (A, B)
        raw = re.sub(r"\s*\(`[^`]*`[^)]*\)", "", raw)   # file paths stay off the public page
        raw = re.sub(r"`[^`]*`", "", raw)
        m = re.search(r"\s--\s([A-Za-z]{3,9}\s+\d{1,2})\s*(\(([^)]*)\))?\s*$", raw)
        wdate, team = None, ""
        text = raw
        if m:
            wdate = parse_win_date(m.group(1), today.year)
            team = (m.group(3) or "").strip()
            text = raw[:m.start()].strip()
        # strip any stray trailing markdown
        text = text.rstrip(" .")
        wins.append({"text": text, "team": team, "date": wdate})

    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=7)
    y = [w for w in wins if w["date"] == yesterday]
    wk = [w for w in wins if w["date"] and week_start <= w["date"] <= today]
    return y, wk


def load_projects(today):
    if not TIMELINE.exists():
        return []
    data = json.loads(TIMELINE.read_text(encoding="utf-8"))
    out = []
    for p in data.get("projects", []):
        if p.get("status") == "done":
            continue
        if p.get("archived"):
            continue
        if is_term_over(p.get("name", ""), today):
            continue
        todo = [t for t in p.get("tasks", []) if not t.get("done")]
        nxt = todo[0]["label"] if todo else "Define the next step"
        out.append({"name": p.get("name", "?"),
                    "status": p.get("status", "on-track"),
                    "next": nxt})
    # surface at-risk first, then on-track, paused last
    order = {"blocked": 0, "at-risk": 1, "on-track": 2, "paused": 3}
    out.sort(key=lambda p: order.get(p["status"], 2))
    return out


def load_workon():
    if not SERENDIPITY.exists():
        return []
    data = json.loads(SERENDIPITY.read_text(encoding="utf-8"))
    picks = []
    for s in data.get("suggestions", [])[:2]:
        picks.append({"verb": s.get("verb", "Try"),
                      "title": s.get("title", ""),
                      "action": s.get("action") or s.get("description", "")})
    return picks


def load_feed():
    if not FEED.exists():
        return {}
    return json.loads(FEED.read_text(encoding="utf-8"))


def shorten(text, n=150):
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def build(today):
    y_wins, wk_wins = load_wins(today)
    projects = load_projects(today)
    workon = load_workon()
    feed = load_feed()
    fresh = str(feed.get("_updated", "")) == today.isoformat()

    # cover line: a warm one-liner summarizing the state of things
    n_week = len(wk_wins)
    n_proj = len(projects)
    at_risk = [p["name"] for p in projects if p["status"] == "at-risk"]
    bits = []
    if n_week:
        bits.append(f"{n_week} thing{'s' if n_week != 1 else ''} shipped this week")
    if n_proj:
        bits.append(f"{n_proj} project{'s' if n_proj != 1 else ''} in motion")
    cover = ". ".join(b.capitalize() if i == 0 else b for i, b in enumerate(bits)) or \
        "A fresh page. Let's see what today wants to be."
    cover += "."
    if at_risk:
        cover += f" Keep an eye on {at_risk[0]}."

    data = {
        "date": today.isoformat(),
        "builtAt": today.isoformat(),
        "dayName": today.strftime("%A"),
        "dateLong": today.strftime("%B %-d, %Y"),
        "coverLine": cover,
        "yesterdayLabel": (today - timedelta(days=1)).strftime("%A"),
        "yesterday": [{"text": shorten(w["text"]), "team": w["team"]} for w in y_wins[:6]],
        "weekWinCount": n_week,
        "weekHighlights": [{"text": shorten(w["text"], 120)} for w in wk_wins[:6]],
        "projects": projects,
        "today": feed.get("today", []),
        "twoWeeks": feed.get("twoWeeks", []),
        "workOn": workon,
        "headlines": feed.get("headlines", []),
        "feedNews": feed.get("feedNews", []),
        "wordCloud": feed.get("wordCloud", []),
        "frontier": feed.get("frontier"),
        # the daily pieces only show on the day they were written, never a day late
        "hook": feed.get("hook") if fresh else None,
        "lead": feed.get("lead") if fresh else None,
        "graph": feed.get("graph") if fresh else None,
        "argue": feed.get("argue") if fresh else None,
        "closeLine": feed.get("closeLine", "Open something. The drop is data."),
        "closeSub": feed.get("closeSub",
                             "Tap through anytime — the briefing rebuilds itself each morning."),
    }

    js = "window.BRIEFING = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    OUT.write_text(js, encoding="utf-8")
    return data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        today = date.today()
    d = build(today)
    print(f"Built briefing for {d['dateLong']}:")
    print(f"  yesterday wins : {len(d['yesterday'])}")
    print(f"  week wins      : {d['weekWinCount']}")
    print(f"  projects       : {len(d['projects'])}")
    print(f"  today events   : {len(d['today'])}")
    print(f"  two-week items : {len(d['twoWeeks'])}")
    print(f"  work-on picks  : {len(d['workOn'])}")
    print(f"  headlines      : {len(d['headlines'])}")
    print(f"  feed news      : {len(d['feedNews'])}")
    print(f"  frontier items : {len((d.get('frontier') or {}).get('items', []))}")
    print(f"  word cloud     : {len(d['wordCloud'])}")
    print(f"  -> {OUT}")

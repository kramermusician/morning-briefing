# Morning Briefing

An auto-playing daily briefing for Kramer, modeled on the welcome-splash aesthetic
(paper/ink palette, Georgia serif, grain, slow orbiting backdrop). Nine slides:

1. **Good morning** — date, day, one-line state of things
2. **Yesterday's wins** — what got done while you were away
3. **This week** — big count + top highlights
4. **The big rocks** — project status board (color-coded, with the next step on each)
5. **Today** — today's calendar
6. **Next two weeks** — upcoming appointments (daily language-habit blocks filtered out)
7. **What to work on** — two ideas pulled from the dashboard's Serendipity engine
8. **The world** — three global headlines
9. **Go make something** — sign-off

## How it updates daily

`build_briefing.py` re-derives the data every run and writes `briefing-data.js`,
which `index.html` reads. Sources:

| Slide | Source | Auto? |
|-------|--------|-------|
| Wins (yesterday + week) | `priorities.md` → "Recently Accomplished" | yes |
| Project board | `project-timeline.json` | yes |
| What to work on | `serendipity.json` | yes |
| Today's calendar | `briefing-feed.json` → `today` | needs a session |
| Next two weeks | `briefing-feed.json` → `twoWeeks` | needs a session |
| Headlines | `briefing-feed.json` → `headlines` | needs a session |

The local-file sections are fully autonomous — `build_briefing.py` can run unattended.
The **feed file** holds the parts that need a connected session: Cadence pulls the
calendar, Pax pulls the day's headlines, both written into `briefing-feed.json`.
If the feed is stale or missing, those slides degrade gracefully (the rest still builds).

## Run it

```bash
./launch.sh                      # rebuild + open
python3 build_briefing.py        # rebuild only (for today)
python3 build_briefing.py 2026-06-12   # rebuild as of a specific date
```

Then open `index.html` in any browser. No build step, no server, works offline.

## Controls

- **space / → / click-right** — next slide
- **← / click-left** — previous
- **p** — pause/resume auto-advance
- **r** — restart from the top
- Auto-advances on its own; denser slides linger a little longer.

## Keeping the feed fresh

Two ways to refresh `briefing-feed.json` each morning:

1. **Ask Larry** — "refresh my morning briefing" pulls today's calendar (Cadence)
   and three headlines (Pax), rewrites the feed, and reruns the builder.
2. **Cron it** — a scheduled cloud agent each morning that does the same, so the
   slideshow is current before you wake up. (Not wired by default — ask to set it up.)

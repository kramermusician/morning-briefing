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

## Live on your phone (GitHub Pages)

Published at **https://kramermusician.github.io/morning-briefing/** from the
public repo `kramermusician/morning-briefing`. Mobile-friendly; tap or swipe to advance.

Pipeline:
- `deploy.sh` — rebuild + commit + push. Pages auto-redeploys (~30 s).
- `nightly.sh` — the unattended job: best-effort feed refresh (calendar + headlines
  via a headless `claude -p`), then rebuild, then push.
- `com.kramos.morning-briefing.plist` — launchd agent at `~/Library/LaunchAgents/`,
  fires daily at **00:05**. Manage with:
  ```bash
  launchctl unload ~/Library/LaunchAgents/com.kramos.morning-briefing.plist
  launchctl load   ~/Library/LaunchAgents/com.kramos.morning-briefing.plist
  launchctl start  com.kramos.morning-briefing   # run it now
  ```
- The Mac must be awake at midnight. Scheduled wake (run once, needs sudo):
  ```bash
  sudo pmset repeat wakeorpoweron MTWRFSU 00:03:00
  ```

### iOS Shortcut (open at 7 am)
1. Shortcuts app → new shortcut → **Open URLs** → `https://kramermusician.github.io/morning-briefing/`
   (add **Open App → Safari** before it if you want it to surface).
2. Automation tab → **Create Personal Automation** → **Time of Day → 7:00 AM, Daily**
   → add the shortcut → turn **Run Immediately** on (off = a tap to confirm).

## Keeping the feed fresh

Two ways to refresh `briefing-feed.json` each morning:

1. **Ask Larry** — "refresh my morning briefing" pulls today's calendar (Cadence)
   and three headlines (Pax), rewrites the feed, and reruns the builder.
2. **Cron it** — a scheduled cloud agent each morning that does the same, so the
   slideshow is current before you wake up. (Not wired by default — ask to set it up.)

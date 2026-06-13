#!/bin/bash
# Nightly job (run by launchd ~00:05): refresh the live feed (best-effort),
# rebuild today's briefing from local files, and publish to GitHub Pages.
cd "$(dirname "$0")"
LOG="nightly.log"
{
  echo ""
  echo "===== $(date) ====="

  # 1. Best-effort: refresh calendar + headlines via a headless Claude session.
  #    If the calendar MCP isn't available headless, this no-ops and the last
  #    feed persists; the build below still refreshes wins/projects/picks.
  if command -v claude >/dev/null 2>&1; then
    if timeout 300 claude -p "$(cat refresh-prompt.txt)" \
         --dangerously-skip-permissions 2>&1; then
      echo "feed refresh: ok"
    else
      echo "feed refresh: skipped/failed (keeping last feed)"
    fi
  fi

  # 1b. Best-effort: refresh the feed word cloud (mechanical, no model needed).
  #     Needs network; if it fails, the last word cloud persists.
  if python3 "$HOME/Desktop/Kramer-Projects-2026/scripts/utilities/briefing_wordcloud.py" \
       --all --max 24 2>&1; then
    echo "wordcloud: ok"
  else
    echo "wordcloud: skipped/failed (keeping last cloud)"
  fi

  # 2. Rebuild data from local files (priorities.md, project-timeline.json, serendipity.json).
  python3 build_briefing.py

  # 3. Publish.
  git add -A
  if git -c user.name="Kramer Gibson" -c user.email="kramermusician@gmail.com" \
       commit -q -m "Nightly briefing $(date +%F)"; then
    git push -q origin main && echo "published"
  else
    echo "no changes to publish"
  fi
} >> "$LOG" 2>&1

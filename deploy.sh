#!/bin/bash
# Rebuild today's briefing from local files and publish to GitHub Pages.
# (wins / projects / work-on picks always refresh; calendar + headlines come
#  from briefing-feed.json, refreshed separately by the nightly job or on demand.)
set -e
cd "$(dirname "$0")"
# Best-effort: refresh the feed word cloud (mechanical; needs network).
python3 "$HOME/Desktop/Kramer-Projects-2026/scripts/utilities/briefing_wordcloud.py" --all --max 24 || echo "wordcloud: skipped (keeping last)"
python3 build_briefing.py
git add -A
if git -c user.name="Kramer Gibson" -c user.email="kramermusician@gmail.com" \
     commit -q -m "Briefing $(date +%F)"; then
  git push -q origin main && echo "Published -> https://kramermusician.github.io/morning-briefing/"
else
  echo "No changes to publish."
fi

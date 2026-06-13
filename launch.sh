#!/bin/bash
# Morning Briefing launcher.
# Rebuilds today's data from the live KRAMOS files, then opens the slideshow.
set -e
cd "$(dirname "$0")"
python3 build_briefing.py
open index.html

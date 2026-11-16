#!/bin/bash
# Optional, per person, on a Mac: the Mac counterpart of schedule.ps1. Registers the launchd job "Claude tracker
# update": weekdays at 17:30 (or --at HH:MM), while you are logged in. If the Mac is asleep at that time, the job runs
# when it wakes; if it was shut down, that day is skipped. It copies scheduled.sh into your settings folder
# (~/.claude/tracker-update) and runs it from there, so plugin updates don't break the job.
#   bash schedule.sh                 set it up (or change the time with --at 18:00)
#   bash schedule.sh --remove        delete it
set -euo pipefail

label="com.defoxx.itg.claude-tracker-update"
agents="$HOME/Library/LaunchAgents"
plist="$agents/$label.plist"
settings="$HOME/.claude/tracker-update"
domain="gui/$(id -u)"
at="17:30"
remove=0

while [ $# -gt 0 ]; do
    case "$1" in
        --remove|-Remove) remove=1 ;;
        --at|-At) at="${2:?--at needs a time, such as 18:00}"; shift ;;
        *) echo "Unknown option: $1 (use --at HH:MM or --remove)" >&2; exit 1 ;;
    esac
    shift
done

if [ "$remove" = 1 ]; then
    launchctl bootout "$domain/$label" 2>/dev/null || true
    rm -f "$plist"
    echo "Removed the job 'Claude tracker update'."
    exit 0
fi

if [[ ! "$at" =~ ^([01]?[0-9]|2[0-3]):([0-5][0-9])$ ]]; then
    echo "Give the time as HH:MM, such as 18:00: $at" >&2
    exit 1
fi
hour=$((10#${BASH_REMATCH[1]}))
minute=$((10#${BASH_REMATCH[2]}))

# The job runs without your shell's PATH, so find Python 3.11+ and claude now and hand their full paths to it.
python=""
for candidate in "$(command -v python3 || true)" /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if [ -n "$candidate" ] && [ -x "$candidate" ] &&
        "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
        python="$candidate"
        break
    fi
done
if [ -z "$python" ]; then
    echo "Python 3.11 or later was not found. Install it (for example: brew install python) and run this again." >&2
    exit 1
fi
claude="$(command -v claude || true)"
[ -n "$claude" ] || claude="$HOME/.local/bin/claude"
if [ ! -x "$claude" ]; then
    echo "The claude command was not found. Install Claude Code and run this again." >&2
    exit 1
fi

here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$settings" "$agents"
launcher="$settings/scheduled.sh"
cp "$here/scheduled.sh" "$launcher"
chmod +x "$launcher"

xml() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

days=""
for weekday in 1 2 3 4 5; do
    days="$days
        <dict><key>Weekday</key><integer>$weekday</integer><key>Hour</key><integer>$hour</integer><key>Minute</key><integer>$minute</integer></dict>"
done

cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$label</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$(xml "$launcher")</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TRACKER_PYTHON</key><string>$(xml "$python")</string>
        <key>TRACKER_CLAUDE</key><string>$(xml "$claude")</string>
    </dict>
    <key>StartCalendarInterval</key>
    <array>$days
    </array>
    <key>StandardErrorPath</key><string>$(xml "$settings/scheduled.log")</string>
</dict>
</plist>
PLIST
plutil -lint "$plist" >/dev/null

launchctl bootout "$domain/$label" 2>/dev/null || true
launchctl bootstrap "$domain" "$plist"
printf "Registered 'Claude tracker update': weekdays at %02d:%02d, running %s.\n" "$hour" "$minute" "$launcher"

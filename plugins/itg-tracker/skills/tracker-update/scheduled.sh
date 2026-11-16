#!/bin/bash
# Run by the Mac job "Claude tracker update": the Mac counterpart of scheduled.ps1. schedule.sh copies this file into
# the person's settings folder (~/.claude/tracker-update), so it keeps working when a plugin update installs the skill
# in a new folder. It finds the installed skill (the itg-tracker plugin first, else a hand copy in ~/.claude/skills),
# and opens a Terminal window with Claude on it only when a work project has something not yet posted. Logs counts
# only. --dry-run does everything except open the window.
set -u -o pipefail

settings="$HOME/.claude/tracker-update"
mkdir -p "$settings"
log="$settings/scheduled.log"
say() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$log"; }
dry=0
[ "${1:-}" = "--dry-run" ] && dry=1

from_plugin="$(ls -t "$HOME"/.claude/plugins/cache/*/itg-tracker/*/skills/tracker-update/tracker.py 2>/dev/null | head -n 1)"
hand_copy="$HOME/.claude/skills/tracker-update/tracker.py"
if [ -n "$from_plugin" ]; then
    tracker="$from_plugin"; prompt="/itg-tracker:tracker-update"
elif [ -f "$hand_copy" ]; then
    tracker="$hand_copy"; prompt="/tracker-update"
else
    say "tracker-update skill not found"; exit 1
fi

python="${TRACKER_PYTHON:-$(command -v python3 || true)}"
if [ -z "$python" ]; then say "python3 not found"; exit 1; fi
if ! pending="$("$python" "$tracker" pending 2>/dev/null | tail -n 1)"; then
    say "tracker.py pending failed"; exit 1
fi
case "$pending" in
    ''|*[!0-9]*) say "tracker.py pending gave no count"; exit 1 ;;
esac
if [ "$pending" -eq 0 ]; then say "nothing pending"; exit 0; fi

claude="${TRACKER_CLAUDE:-$HOME/.local/bin/claude}"
[ -x "$claude" ] || claude="$(command -v claude || true)"
if [ -z "$claude" ]; then say "claude not found"; exit 1; fi

# A .command file opens in a new Terminal window without asking for permission to control Terminal.
window="$settings/open-claude.command"
printf '#!/bin/bash\ncd "$HOME" || exit 1\nexec %q --chrome %q\n' "$claude" "$prompt" > "$window"
chmod +x "$window"
if [ "$dry" = 1 ]; then
    say "$pending pending: would open Claude (dry run)"
    echo "$pending pending: would open Claude with $prompt"
    exit 0
fi
open -a Terminal "$window"
say "$pending pending: opened Claude"

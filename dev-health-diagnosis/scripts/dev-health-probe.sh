#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_DIR/dev_health_probe.py" "$@"
fi

printf 'dev-health-probe requires python3 for structured and redacted output.\n' >&2
printf 'Fallback checks you can run manually:\n' >&2
printf '  time zsh -lc '"'"'exit'"'"'\n' >&2
printf '  time zsh -f -lc '"'"'exit'"'"'\n' >&2
printf '  time bash -lc '"'"'exit'"'"'\n' >&2
printf '  time bash --noprofile --norc -lc '"'"'exit'"'"'\n' >&2
exit 127

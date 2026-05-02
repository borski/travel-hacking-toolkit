#!/bin/bash
# Start virtual display for Patchright headed mode
Xvfb :99 -screen 0 1440x900x24 -nolisten tcp &
export DISPLAY=:99
sleep 1

# Route to the right script:
#   "change" or "check" -> check_change.py (login, check prices, list trips)
#   "monitor"            -> monitor.py     (compare booked baselines vs current)
#   "search" or flags    -> search_fares.py (new flight search)
cmd="$1"
case "$cmd" in
    change|check)
        shift
        python3 /app/check_change.py "$@"
        ;;
    monitor)
        shift
        python3 /app/monitor.py "$@"
        ;;
    search)
        shift
        python3 /app/search_fares.py "$@"
        ;;
    *)
        # Default: if first arg starts with -- it's a flag for search_fares
        python3 /app/search_fares.py "$@"
        ;;
esac

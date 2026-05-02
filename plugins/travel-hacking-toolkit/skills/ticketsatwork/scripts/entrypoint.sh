#!/bin/bash
# Start virtual display for Patchright headed mode (xvfb avoids TaW's
# bot detection without opening a window on the host).
Xvfb :99 -screen 0 1440x900x24 -nolisten tcp &
export DISPLAY=:99
sleep 1

# Subcommand router. Routes to the appropriate TaW search script.
#   "search-hotels"  | "hotels"  -> search_hotels.py
#   "search-cars"    | "cars"    -> search_cars.py
#   "browse-tickets" | "tickets" -> browse_tickets.py
#   default                      -> search_hotels.py (most common use)
cmd="$1"
case "$cmd" in
    search-hotels|hotels)
        shift
        python3 /app/search_hotels.py "$@"
        ;;
    search-cars|cars)
        shift
        python3 /app/search_cars.py "$@"
        ;;
    browse-tickets|tickets)
        shift
        python3 /app/browse_tickets.py "$@"
        ;;
    *)
        # Default to hotels search if first arg looks like a flag (e.g. --city)
        python3 /app/search_hotels.py "$@"
        ;;
esac

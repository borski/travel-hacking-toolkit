#!/bin/bash
# Start a virtual display so Patchright can run headed.
Xvfb :99 -screen 0 1440x900x24 -nolisten tcp &
export DISPLAY=:99
sleep 1

exec python3 /app/search_viajanet.py "$@"

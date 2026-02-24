#!/bin/bash
# Clean up stale lock files
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

# Start Xvfb for virtual display (prevents GPU/font rendering issues)
Xvfb :99 -screen 0 1600x1200x24 -nolisten tcp &
export DISPLAY=:99

# Wait for Xvfb to start
sleep 2

exec python3 /app/launch_server.py

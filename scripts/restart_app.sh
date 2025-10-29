#!/usr/bin/env bash
set -euo pipefail

# Restart the Flask app reliably: kill any running copies and start with nohup.
# Logs are written to /tmp/face-app.log

echo "Stopping any running app.py processes..."
pkill -f "/workspaces/face-detection-system/app.py" || true
sleep 0.3

echo "Starting app.py with nohup (logs -> /tmp/face-app.log)..."
nohup python3 /workspaces/face-detection-system/app.py > /tmp/face-app.log 2>&1 &

# Give it a moment to start
sleep 0.8

echo "Processes:"
ps aux | grep -E "[a]pp.py|/workspaces/face-detection-system/app.py" || true

echo "--- last 80 lines of /tmp/face-app.log ---"
if [ -f /tmp/face-app.log ]; then
  tail -n 80 /tmp/face-app.log
else
  echo "/tmp/face-app.log not found"
fi

exit 0

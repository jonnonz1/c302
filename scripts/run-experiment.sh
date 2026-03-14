#!/usr/bin/env bash
##
# @file run-experiment.sh
# @description Run a single c302 experiment end-to-end.
#
# Orchestrates the full experiment lifecycle:
#   1. Start the worm-bridge controller server (background)
#   2. Reset demo-repo to its baseline state (CRUD works, search fails)
#   3. Run the agent control loop (agent <-> controller ticks)
#   4. Collect all trace files into research/experiments/<experiment-id>/
#
# When RECORD=1, the dashboard captures per-tick screenshots via html2canvas
# and builds a WebM video in-browser. The video is uploaded back to the server
# and saved to the experiment output directory. This runs entirely in the
# background — no screen region is captured, so you can keep using your machine.
#
# @usage ./scripts/run-experiment.sh <controller-type> [experiment-id]
#   controller-type: static | synthetic | replay | live | plastic
#   experiment-id:   optional, defaults to <controller>-<YYYYMMDD-HHMMSS>
#
# @envvar RECORD=1  Enable video capture via the dashboard
#
# @project c302
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
WORM_BRIDGE_PID=""
WORM_BRIDGE_PORT="${WORM_BRIDGE_PORT:-8642}"
MAX_ITERATIONS="${MAX_ITERATIONS:-30}"
VALID_CONTROLLERS="static synthetic replay live plastic random"
RECORD="${RECORD:-0}"

## @fn cleanup
## @description Gracefully terminate background processes on script exit.
cleanup() {
  if [ -n "$WORM_BRIDGE_PID" ]; then
    echo ""
    echo "Stopping worm-bridge server (PID: $WORM_BRIDGE_PID)..."
    kill "$WORM_BRIDGE_PID" 2>/dev/null || true
    # Grace period then force-kill (uvicorn hangs if browser tabs hold connections)
    sleep 2
    kill -9 "$WORM_BRIDGE_PID" 2>/dev/null || true
    wait "$WORM_BRIDGE_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

# Load .env if present
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set."
  echo "  Set it in .env or export it before running."
  exit 1
fi

if [ $# -lt 1 ]; then
  echo "ERROR: controller-type is required."
  echo "Usage: $0 <controller-type> [experiment-id]"
  echo "  controller-type: $VALID_CONTROLLERS"
  exit 1
fi

CONTROLLER="$1"
EXPERIMENT_ID="${2:-${CONTROLLER}-$(date +%Y%m%d-%H%M%S)}"

if ! echo "$VALID_CONTROLLERS" | grep -qw "$CONTROLLER"; then
  echo "ERROR: Invalid controller type '$CONTROLLER'."
  echo "  Valid types: $VALID_CONTROLLERS"
  exit 1
fi

OUTPUT_DIR="$PROJECT_ROOT/research/experiments/$EXPERIMENT_ID"
mkdir -p "$OUTPUT_DIR"

echo "=== c302 Experiment ==="
echo "  Controller:    $CONTROLLER"
echo "  Experiment ID: $EXPERIMENT_ID"
echo "  Output:        $OUTPUT_DIR"
echo "  Max ticks:     $MAX_ITERATIONS"
echo "  Recording:     $([ "$RECORD" = "1" ] && echo "ON" || echo "OFF")"
echo ""

# Step 1: Build the agent
echo "[1/4] Building agent..."
cd "$PROJECT_ROOT"
npx tsc -p packages/agent/tsconfig.json

# Step 2: Start worm-bridge server
echo "[2/4] Starting worm-bridge server (port $WORM_BRIDGE_PORT, controller=$CONTROLLER)..."
CONTROLLER_TYPE="$CONTROLLER" \
  OUTPUT_DIR="$OUTPUT_DIR" \
  "$PROJECT_ROOT/worm-bridge/.venv/bin/uvicorn" \
  worm_bridge.server:app \
  --port "$WORM_BRIDGE_PORT" \
  --app-dir "$PROJECT_ROOT/worm-bridge" \
  &> "$OUTPUT_DIR/worm-bridge.log" &
WORM_BRIDGE_PID=$!

# Wait for server to be ready
echo "  Waiting for server..."
for i in $(seq 1 30); do
  if curl -sf "http://localhost:$WORM_BRIDGE_PORT/health" > /dev/null 2>&1; then
    echo "  Server ready."
    break
  fi
  if ! kill -0 "$WORM_BRIDGE_PID" 2>/dev/null; then
    echo "ERROR: worm-bridge server failed to start. Check $OUTPUT_DIR/worm-bridge.log"
    exit 1
  fi
  sleep 0.5
done

if ! curl -sf "http://localhost:$WORM_BRIDGE_PORT/health" > /dev/null 2>&1; then
  echo "ERROR: worm-bridge server did not become ready. Check $OUTPUT_DIR/worm-bridge.log"
  exit 1
fi

# Open dashboard for recording if enabled
if [ "$RECORD" = "1" ]; then
  DASHBOARD_URL="http://localhost:$WORM_BRIDGE_PORT/dashboard/?record=1"
  echo "[rec] Opening dashboard: $DASHBOARD_URL"
  open "$DASHBOARD_URL"
  sleep 2
fi

# Step 3: Reset demo-repo to baseline
echo "[3/4] Resetting demo-repo to baseline..."
"$SCRIPT_DIR/reset-demo-repo.sh"

# Step 4: Run the agent loop
echo "[4/4] Running agent loop..."
CONTROLLER_URL="http://localhost:$WORM_BRIDGE_PORT" \
  CONTROLLER_TYPE="$CONTROLLER" \
  REPO_PATH="$PROJECT_ROOT/demo-repo" \
  MAX_ITERATIONS="$MAX_ITERATIONS" \
  OUTPUT_DIR="$OUTPUT_DIR" \
  node "$PROJECT_ROOT/packages/agent/dist/index.js"

echo ""

# Signal the dashboard to finish recording and save the video
if [ "$RECORD" = "1" ]; then
  echo "[rec] Signalling experiment complete..."
  curl -sf -X POST "http://localhost:$WORM_BRIDGE_PORT/ingest" \
    -H "Content-Type: application/json" \
    -d '{"experiment_complete": true}' > /dev/null 2>&1 || true

  echo "[rec] Waiting for video to be saved..."
  for i in $(seq 1 60); do
    if [ -f "$OUTPUT_DIR/experiment.webm" ]; then
      SIZE=$(du -h "$OUTPUT_DIR/experiment.webm" | cut -f1)
      echo "[rec] Video saved: $OUTPUT_DIR/experiment.webm ($SIZE)"
      break
    fi
    sleep 1
  done

  if [ ! -f "$OUTPUT_DIR/experiment.webm" ]; then
    echo "[rec] Warning: video not saved within timeout. Check the browser tab for download."
  fi
fi

echo "=== Experiment complete ==="
echo "  Results: $OUTPUT_DIR"

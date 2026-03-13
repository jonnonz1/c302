#!/usr/bin/env bash
##
# @file Run a single c302 experiment.
#
# Starts the worm-bridge server, resets the demo-repo, runs the agent loop,
# and collects results into research/experiments/.
# The worm-bridge server is stopped on exit via trap.
#
# Usage: ./scripts/run-experiment.sh <controller-type> [experiment-id]
#   controller-type: static | synthetic | replay | live | plastic
#   experiment-id:   optional, defaults to <controller>-<timestamp>
#
# @project c302
# @phase 0 (placeholder — agent loop added in Phase 1+)
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
WORM_BRIDGE_PID=""

VALID_CONTROLLERS="static synthetic replay live plastic"

cleanup() {
  if [ -n "$WORM_BRIDGE_PID" ]; then
    echo "Stopping worm-bridge server (PID: $WORM_BRIDGE_PID)..."
    kill "$WORM_BRIDGE_PID" 2>/dev/null || true
    wait "$WORM_BRIDGE_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

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
echo ""

echo "run-experiment.sh: Not yet implemented. Phase 1+ will add the agent loop."
echo ""
echo "Planned steps:"
echo "  1. Start worm-bridge server with controller=$CONTROLLER"
echo "  2. Reset demo-repo to baseline"
echo "  3. Run agent loop"
echo "  4. Capture results to $OUTPUT_DIR"

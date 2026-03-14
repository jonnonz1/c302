#!/usr/bin/env bash
##
# @file run-battery.sh
# @description Run a battery of N experiments for a given controller type.
#
# Features:
#   - Graceful stop on Ctrl-C (finishes current run, prints summary)
#   - Tracks pass/fail per run with exit codes
#   - Prints a summary table at the end
#   - Logs everything to a battery-level log file
#   - Supports resuming (skips existing completed runs)
#
# @usage ./scripts/run-battery.sh <controller-type> <num-runs> [battery-id]
#   controller-type: static | synthetic | random | replay | live | plastic
#   num-runs:        number of experiments to run
#   battery-id:      optional, defaults to <controller>-battery-<YYYYMMDD-HHMMSS>
#
# @envvar MAX_ITERATIONS  Max ticks per run (default: 30)
# @envvar RESUME=1        Skip runs whose output directory already exists
#
# @project c302
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
STOP_REQUESTED=0
RESUME="${RESUME:-0}"

handle_signal() {
  echo ""
  echo "[battery] Stop requested — finishing current run then stopping..."
  STOP_REQUESTED=1
}

trap handle_signal INT TERM

if [ $# -lt 2 ]; then
  echo "Usage: $0 <controller-type> <num-runs> [battery-id]"
  echo ""
  echo "  controller-type: static | synthetic | random | replay | live | plastic"
  echo "  num-runs:        number of experiments (e.g. 20)"
  echo "  battery-id:      optional label (default: <controller>-battery-<timestamp>)"
  echo ""
  echo "Environment:"
  echo "  MAX_ITERATIONS=30   Max ticks per run"
  echo "  RESUME=1            Skip runs whose output already exists"
  exit 1
fi

CONTROLLER="$1"
NUM_RUNS="$2"
BATTERY_ID="${3:-${CONTROLLER}-battery-$(date +%Y%m%d-%H%M%S)}"
BATTERY_DIR="$PROJECT_ROOT/research/experiments"
LOG_FILE="$BATTERY_DIR/${BATTERY_ID}.log"

declare -a RESULTS=()
PASSED=0
FAILED=0
SKIPPED=0

mkdir -p "$BATTERY_DIR"

echo "=== c302 Battery ===" | tee "$LOG_FILE"
echo "  Controller:  $CONTROLLER" | tee -a "$LOG_FILE"
echo "  Runs:        $NUM_RUNS" | tee -a "$LOG_FILE"
echo "  Battery ID:  $BATTERY_ID" | tee -a "$LOG_FILE"
echo "  Max ticks:   ${MAX_ITERATIONS:-30}" | tee -a "$LOG_FILE"
echo "  Resume:      $RESUME" | tee -a "$LOG_FILE"
echo "  Started:     $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Build once before the loop
echo "[battery] Building agent..." | tee -a "$LOG_FILE"
cd "$PROJECT_ROOT"
npx tsc -p packages/agent/tsconfig.json 2>&1 | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

for i in $(seq 1 "$NUM_RUNS"); do
  if [ "$STOP_REQUESTED" -eq 1 ]; then
    echo "[battery] Stopped by user at run $i/$NUM_RUNS" | tee -a "$LOG_FILE"
    break
  fi

  RUN_ID="${BATTERY_ID}-$(printf '%02d' "$i")"
  RUN_DIR="$BATTERY_DIR/$RUN_ID"

  # Resume support — skip if output exists and has trace data
  if [ "$RESUME" = "1" ] && [ -d "$RUN_DIR" ] && [ -f "$RUN_DIR/worm-bridge.log" ]; then
    echo "[battery] [$i/$NUM_RUNS] $RUN_ID — skipped (already exists)" | tee -a "$LOG_FILE"
    RESULTS+=("SKIP")
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  echo "[battery] [$i/$NUM_RUNS] $RUN_ID — starting..." | tee -a "$LOG_FILE"
  START_TIME=$(date +%s)

  if SKIP_BUILD=1 "$SCRIPT_DIR/run-experiment.sh" "$CONTROLLER" "$RUN_ID" 2>&1 | tee -a "$LOG_FILE"; then
    ELAPSED=$(( $(date +%s) - START_TIME ))
    echo "[battery] [$i/$NUM_RUNS] $RUN_ID — PASS (${ELAPSED}s)" | tee -a "$LOG_FILE"
    RESULTS+=("PASS")
    PASSED=$((PASSED + 1))
  else
    EXIT_CODE=$?
    ELAPSED=$(( $(date +%s) - START_TIME ))
    echo "[battery] [$i/$NUM_RUNS] $RUN_ID — FAIL (exit $EXIT_CODE, ${ELAPSED}s)" | tee -a "$LOG_FILE"
    RESULTS+=("FAIL")
    FAILED=$((FAILED + 1))
  fi

  echo "" | tee -a "$LOG_FILE"
done

COMPLETED=$((PASSED + FAILED))
TOTAL=$((COMPLETED + SKIPPED))

echo "=== Battery Summary ===" | tee -a "$LOG_FILE"
echo "  Controller:  $CONTROLLER" | tee -a "$LOG_FILE"
echo "  Completed:   $COMPLETED / $NUM_RUNS" | tee -a "$LOG_FILE"
echo "  Passed:      $PASSED" | tee -a "$LOG_FILE"
echo "  Failed:      $FAILED" | tee -a "$LOG_FILE"
if [ "$SKIPPED" -gt 0 ]; then
  echo "  Skipped:     $SKIPPED (resume)" | tee -a "$LOG_FILE"
fi
echo "  Finished:    $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "  Run results:" | tee -a "$LOG_FILE"
for i in $(seq 1 "$TOTAL"); do
  RUN_ID="${BATTERY_ID}-$(printf '%02d' "$i")"
  STATUS="${RESULTS[$((i - 1))]}"
  case "$STATUS" in
    PASS) ICON="+" ;;
    FAIL) ICON="x" ;;
    SKIP) ICON="-" ;;
  esac
  echo "    [$ICON] $RUN_ID" | tee -a "$LOG_FILE"
done

echo "" | tee -a "$LOG_FILE"
echo "  Log: $LOG_FILE" | tee -a "$LOG_FILE"

if [ "$STOP_REQUESTED" -eq 1 ]; then
  echo ""
  echo "  Battery was stopped early. Resume with:"
  echo "    RESUME=1 $0 $CONTROLLER $NUM_RUNS $BATTERY_ID"
fi

exit "$FAILED"

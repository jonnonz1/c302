#!/usr/bin/env bash
##
# @file Run comparison experiments across all controller types.
#
# Runs the same task with each controller type sequentially,
# then generates comparison figures. Each controller is run
# N times (default 1) to allow statistical comparison.
#
# Usage: ./scripts/run-comparison.sh [num-runs-per-controller]
#
# @project c302
# @phase 0 (placeholder — comparison logic added in Phase 2+)
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NUM_RUNS="${1:-1}"
CONTROLLERS="static synthetic replay live"

echo "=== c302 Comparison Run ==="
echo "  Controllers: $CONTROLLERS"
echo "  Runs each:   $NUM_RUNS"
echo ""

echo "run-comparison.sh: Not yet implemented. Phase 2+ will add comparison runs."
echo ""
echo "Planned: run $NUM_RUNS experiment(s) per controller via run-experiment.sh"

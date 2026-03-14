#!/usr/bin/env bash
##
# @file run-comparison.sh
# @description Run comparison experiments across all controller types.
#
# Executes the same coding task with each controller variant sequentially,
# then generates comparison figures. Each controller is run N times
# (default 1) to provide statistical baselines for comparing controller
# performance (convergence speed, final reward, mode distribution).
#
# Results are written to research/experiments/ with auto-generated IDs.
# After all runs complete, generate-figures.sh is invoked to produce
# comparison plots.
#
# @usage ./scripts/run-comparison.sh [num-runs-per-controller]
#   num-runs-per-controller: number of experiment runs per controller (default: 1)
#
# @project c302
# @phase 0 (placeholder -- comparison logic added in Phase 2+)
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

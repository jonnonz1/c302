#!/usr/bin/env bash
##
# @file capture-video.sh
# @description Capture a video of an experiment run.
#
# Thin wrapper around run-experiment.sh that enables video recording.
# Records the dashboard browser window via macOS screencapture and
# produces an MP4 in the experiment output directory.
#
# @usage ./scripts/capture-video.sh <controller-type> [experiment-id]
#   controller-type: static | synthetic | replay | live | plastic
#
# @project c302
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

RECORD=1 exec "$SCRIPT_DIR/run-experiment.sh" "$@"

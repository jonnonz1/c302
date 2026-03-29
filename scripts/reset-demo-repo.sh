#!/usr/bin/env bash
##
# @file reset-demo-repo.sh
# @description Reset the demo-repo to its baseline state for a clean experiment.
#
# Performs a hard git reset of demo-repo/ to the baseline commit,
# restoring the state where the target tests fail. Also removes any
# untracked files via git clean.
#
# The baseline commit can be set via DEMO_BASELINE env var:
#   - If set: resets to that specific commit hash
#   - If not set: resets to HEAD (the latest commit)
#
# Called by run-experiment.sh before each experiment run.
#
# @usage ./scripts/reset-demo-repo.sh
# @envvar DEMO_BASELINE  Commit hash to reset to (default: HEAD)
#
# @project c302
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEMO_DIR="$SCRIPT_DIR/../demo-repo"

if [ ! -d "$DEMO_DIR/.git" ]; then
  echo "ERROR: demo-repo is not a git repo. Run 'cd demo-repo && git init && git add -A && git commit -m initial' first."
  exit 1
fi

cd "$DEMO_DIR"

BASELINE="${DEMO_BASELINE:-HEAD}"
TARGET=$(git rev-parse "$BASELINE")
git reset --hard "$TARGET"
git clean -fd

echo "demo-repo reset to $BASELINE: $TARGET"

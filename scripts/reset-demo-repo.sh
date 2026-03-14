#!/usr/bin/env bash
##
# @file reset-demo-repo.sh
# @description Reset the demo-repo to its baseline state for a clean experiment.
#
# Performs a hard git reset of demo-repo/ to the initial commit,
# restoring the state where CRUD tests pass and search tests fail.
# Also removes any untracked files via git clean.
#
# This is the canonical starting point for all experiments: the agent's
# task is to make the search tests pass without breaking the CRUD tests.
#
# Called by run-experiment.sh before each experiment run.
#
# @usage ./scripts/reset-demo-repo.sh
#
# @project c302
# @phase 0
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEMO_DIR="$SCRIPT_DIR/../demo-repo"

if [ ! -d "$DEMO_DIR/.git" ]; then
  echo "ERROR: demo-repo is not a git repo. Run 'cd demo-repo && git init && git add -A && git commit -m initial' first."
  exit 1
fi

cd "$DEMO_DIR"

INITIAL_COMMIT=$(git rev-list --max-parents=0 HEAD)
git reset --hard "$INITIAL_COMMIT"
git clean -fd

echo "demo-repo reset to initial commit: $INITIAL_COMMIT"

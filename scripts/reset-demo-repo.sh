#!/usr/bin/env bash
##
# @file Reset the demo-repo to its baseline state.
#
# Performs a hard git reset of demo-repo/ to the initial commit,
# restoring the state where CRUD works and search tests fail.
# Used between experiment runs to ensure a clean starting point.
#
# Usage: ./scripts/reset-demo-repo.sh
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

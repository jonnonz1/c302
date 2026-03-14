##
# @file Top-level Makefile for the c302 monorepo.
#
# Provides unified commands for installing dependencies, building,
# testing, and running experiments across all sub-projects.
#
# @project c302
# @phase 0
##

.PHONY: install build test test-demo clean worm-bridge-dev agent-dev reset-demo analyze \
       battery-static battery-random battery-synthetic battery-all

install:
	npm install
	cd worm-bridge && pip install -e ".[dev]"
	cd demo-repo && npm install

build:
	npm run build

test:
	npm run test
	cd worm-bridge && pytest
	cd demo-repo && npm test

test-demo:
	cd demo-repo && npm test

clean:
	npm run clean
	rm -rf worm-bridge/__pycache__ worm-bridge/.pytest_cache

worm-bridge-dev:
	cd worm-bridge && uvicorn worm_bridge.server:app --reload --port 8642

agent-dev:
	cd packages/agent && npm run dev

reset-demo:
	./scripts/reset-demo-repo.sh

analyze:
	@if [ -z "$(DIR)" ]; then echo "Usage: make analyze DIR=research/experiments/<id>"; exit 1; fi
	cd worm-bridge && python -m worm_bridge.cli analyze ../$(DIR)

BATTERY_RUNS ?= 20

battery-static:
	./scripts/run-battery.sh static $(BATTERY_RUNS)

battery-random:
	./scripts/run-battery.sh random $(BATTERY_RUNS)

battery-synthetic:
	./scripts/run-battery.sh synthetic $(BATTERY_RUNS)

battery-all: battery-static battery-random battery-synthetic

"""CLI entry point for c302 analysis tools.

Usage:
    python -m worm_bridge.cli analyze research/experiments/<id>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from worm_bridge.analysis import analyze


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run analysis on an experiment directory."""
    experiment_dir = Path(args.experiment_dir)
    if not experiment_dir.exists():
        print(f"Error: directory not found: {experiment_dir}", file=sys.stderr)
        sys.exit(1)

    results = analyze(experiment_dir)

    output_path = experiment_dir / "analysis.json"
    output_path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Analysis written to {output_path}")

    convergence = results.get("convergence", {})
    diversity = results.get("behavioral_diversity", {})
    efficiency = results.get("token_efficiency", {})

    print(f"\nConvergence: first_positive_tick={convergence.get('first_positive_reward_tick')}"
          f"  final_pass_rate={convergence.get('final_pass_rate')}")
    print(f"Diversity:   entropy={diversity.get('entropy')}  modes={diversity.get('unique_modes')}")
    print(f"Efficiency:  reward/1k_tokens={efficiency.get('reward_per_1k_tokens')}"
          f"  positive_pct={efficiency.get('positive_tick_pct')}")

    moments = results.get("critical_moments", [])
    if moments:
        print(f"\nTop critical moments:")
        for m in moments[:3]:
            print(f"  tick {m['tick']}: delta={m['reward_delta']:+.3f}  mode={m['mode']}  tools={m.get('tools_used', [])}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="worm_bridge.cli", description="c302 analysis tools")
    sub = parser.add_subparsers(dest="command")

    analyze_parser = sub.add_parser("analyze", help="Analyze experiment traces")
    analyze_parser.add_argument("experiment_dir", help="Path to experiment directory")

    args = parser.parse_args()
    if args.command == "analyze":
        cmd_analyze(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
backend/cli.py — Phase 1 CLI entry point.

Usage (from project root):
    .venv\\Scripts\\python backend\\cli.py \\
        --scenario "A government mandates vaccines for all citizens" \\
        --agents 50 \\
        --rounds 5

Prints:
    - Dominant outcome verdict with confidence percentage
    - Top 3 influential agents
    - 3–5 sentence narrative arc
"""
import argparse
import asyncio
import logging
import sys
import traceback
import uuid

# Configure logging BEFORE importing any backend modules that use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,  # logs go to stderr; CLI output goes to stdout
)

logger = logging.getLogger(__name__)


async def run_cli(
    scenario: str,
    agent_count: int,
    rounds: int,
    seed: int,
) -> None:
    """
    Core async CLI runner. Imports are deferred so sys.path is set before import.
    """
    from simulation.orchestrator import run_simulation

    print(f"\n{'='*60}")
    print("ASim Phase 1 — Starting Simulation")
    print(f"{'='*60}")
    print(f"Scenario : {scenario}")
    print(f"Agents   : {agent_count}")
    print(f"Rounds   : {rounds}")
    print(f"Seed     : {seed}")
    print(f"{'='*60}\n")

    result = await run_simulation(
        scenario=scenario,
        agent_count=agent_count,
        rounds=rounds,
        seed=seed,
    )

    # ── Print formatted output ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("=== ASim Phase 1 Result ===")
    print(f"{'='*60}")
    print(f"Scenario: {scenario}")
    print()
    print(f"Verdict:    {result.verdict}")
    print(f"Confidence: {result.confidence:.0%}")
    dist = result.distribution
    print(f"Support {dist['support']:.0%}  |  Oppose {dist['oppose']:.0%}  |  Undecided {dist['undecided']:.0%}")
    print()
    print("Top Influential Agents:")
    for i, entry in enumerate(result.top_agents, start=1):
        ag, st = entry["agent"], entry["state"]
        print(f"  {i}. {ag.name} ({ag.archetype}) — stance {st.stance:.2f}, emotion: {st.emotion}")
    print()
    print("Narrative Arc:")
    import textwrap
    print(textwrap.fill(result.narrative, width=80))
    print(f"\n{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ASim Phase 1 CLI — run a multi-agent social simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  .venv\\Scripts\\python backend\\cli.py --scenario "A government mandates vaccines" --agents 50 --rounds 5
  .venv\\Scripts\\python backend\\cli.py --scenario "Universal basic income is proposed" --agents 20 --rounds 3
""",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        help="The scenario or policy question for agents to respond to.",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=50,
        help="Number of agents to simulate (default: 50).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=5,
        help="Number of simulation rounds (default: 5).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            run_cli(
                scenario=args.scenario,
                agent_count=args.agents,
                rounds=args.rounds,
                seed=args.seed,
            )
        )
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception:
        print("\n[FATAL] Simulation failed with unhandled exception:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Ensure backend/ is on sys.path when run as: python backend/cli.py
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    main()

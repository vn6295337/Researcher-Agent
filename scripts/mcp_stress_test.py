#!/usr/bin/env python3
"""
MCP Server Stress Test CLI

Usage:
    python scripts/mcp_stress_test.py --mode smoke
    python scripts/mcp_stress_test.py --mode standard --output reports/
    python scripts/mcp_stress_test.py --mode stress --batch-size 100
"""

import asyncio
import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.mcp_reliability.company_sampler import CompanySampler, SamplingStrategy
from tests.mcp_reliability.rate_limiter import get_rate_limiter_registry
from tests.mcp_reliability.circuit_breaker import get_circuit_breaker_registry
from tests.mcp_reliability.test_stress import MCPTestRunner, TestConfig


# Test mode configurations
TEST_MODES = {
    "smoke": {
        "batch_size": 5,
        "sampling_strategy": "uniform",
        "max_concurrent": 3,
        "description": "Quick smoke test for basic functionality"
    },
    "standard": {
        "batch_size": 50,
        "sampling_strategy": "mixed",
        "max_concurrent": 5,
        "description": "Standard reliability test"
    },
    "stress": {
        "batch_size": 100,
        "sampling_strategy": "uniform",
        "max_concurrent": 10,
        "request_interval_ms": 50,
        "description": "High-load stress test"
    },
    "soak": {
        "batch_size": 200,
        "sampling_strategy": "stratified",
        "max_concurrent": 5,
        "description": "Long-running soak test"
    }
}


def print_banner():
    """Print CLI banner."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║           MCP Server Stress Test Framework                ║
║     High-frequency reliability testing for MCP servers    ║
╚═══════════════════════════════════════════════════════════╝
""")


def print_summary(summary: dict):
    """Print formatted test summary."""
    print("\n" + "="*60)
    print("                    TEST SUMMARY")
    print("="*60)

    print(f"\nTotal Requests: {summary['total']}")
    print(f"Success Rate:   {summary['success_rate']*100:.1f}%")
    print(f"Fallback Rate:  {summary['fallback_rate']*100:.1f}%")
    print(f"Failure Rate:   {summary['failure_rate']*100:.1f}%")

    print(f"\nLatency Percentiles:")
    print(f"  P50: {summary['latency_p50']:.0f}ms")
    print(f"  P95: {summary['latency_p95']:.0f}ms")
    print(f"  P99: {summary['latency_p99']:.0f}ms")

    print(f"\nResults by Category:")
    for category, count in summary['by_category'].items():
        if count > 0:
            pct = count / summary['total'] * 100
            print(f"  {category:15s}: {count:4d} ({pct:5.1f}%)")

    print(f"\nResults by Server:")
    for server, cats in summary['by_server'].items():
        total = sum(cats.values())
        success = cats.get('success', 0) + cats.get('partial', 0) + cats.get('fallback', 0)
        rate = success / total * 100 if total > 0 else 0
        print(f"  {server:20s}: {rate:5.1f}% success ({total} requests)")

    # Circuit breaker status
    cb_status = summary.get('circuit_breaker_status', {})
    open_breakers = [name for name, s in cb_status.items() if s.get('state') == 'open']
    if open_breakers:
        print(f"\n⚠️  Open Circuit Breakers: {', '.join(open_breakers)}")

    print("\n" + "="*60)


def check_exit_criteria(summary: dict, mode: str) -> bool:
    """Check if test results meet exit criteria."""
    criteria = {
        "smoke": {"success_rate": 0.95, "p99_latency": 5000, "failure_rate": 0.0},
        "standard": {"success_rate": 0.90, "p99_latency": 10000, "failure_rate": 0.05},
        "stress": {"success_rate": 0.85, "p99_latency": 15000, "failure_rate": 0.10},
        "soak": {"success_rate": 0.85, "p99_latency": 15000, "failure_rate": 0.10}
    }

    c = criteria.get(mode, criteria["standard"])

    passed = True
    print("\nExit Criteria Check:")

    effective_success = summary['success_rate'] + summary['fallback_rate']
    if effective_success >= c["success_rate"]:
        print(f"  ✓ Success rate {effective_success*100:.1f}% >= {c['success_rate']*100:.0f}%")
    else:
        print(f"  ✗ Success rate {effective_success*100:.1f}% < {c['success_rate']*100:.0f}%")
        passed = False

    if summary['latency_p99'] <= c["p99_latency"]:
        print(f"  ✓ P99 latency {summary['latency_p99']:.0f}ms <= {c['p99_latency']}ms")
    else:
        print(f"  ✗ P99 latency {summary['latency_p99']:.0f}ms > {c['p99_latency']}ms")
        passed = False

    if summary['failure_rate'] <= c["failure_rate"]:
        print(f"  ✓ Failure rate {summary['failure_rate']*100:.1f}% <= {c['failure_rate']*100:.0f}%")
    else:
        print(f"  ✗ Failure rate {summary['failure_rate']*100:.1f}% > {c['failure_rate']*100:.0f}%")
        passed = False

    return passed


async def run_test(config: TestConfig) -> dict:
    """Run the stress test with given configuration."""
    runner = MCPTestRunner(config)
    return await runner.run()


def main():
    parser = argparse.ArgumentParser(
        description="MCP Server Stress Test CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/mcp_stress_test.py --mode smoke
  python scripts/mcp_stress_test.py --mode standard --output reports/
  python scripts/mcp_stress_test.py --batch-size 100 --strategy stratified
        """
    )

    parser.add_argument(
        "--mode", "-m",
        choices=list(TEST_MODES.keys()),
        default="standard",
        help="Test mode (default: standard)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        help="Override batch size"
    )
    parser.add_argument(
        "--strategy", "-s",
        choices=["uniform", "stratified", "edge_case", "mixed"],
        help="Override sampling strategy"
    )
    parser.add_argument(
        "--max-concurrent", "-c",
        type=int,
        help="Override max concurrent requests"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output directory for results"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON only"
    )
    parser.add_argument(
        "--servers",
        nargs="+",
        help="Specific servers to test"
    )

    args = parser.parse_args()

    if not args.json:
        print_banner()

    # Build configuration
    mode_config = TEST_MODES[args.mode]

    config = TestConfig(
        batch_size=args.batch_size or mode_config["batch_size"],
        sampling_strategy=args.strategy or mode_config["sampling_strategy"],
        max_concurrent=args.max_concurrent or mode_config.get("max_concurrent", 5),
        request_interval_ms=mode_config.get("request_interval_ms", 200),
        seed=args.seed or int(time.time()),
        servers=args.servers
    )

    if not args.json:
        print(f"Mode: {args.mode} - {mode_config['description']}")
        print(f"Batch size: {config.batch_size}")
        print(f"Strategy: {config.sampling_strategy}")
        print(f"Max concurrent: {config.max_concurrent}")
        print(f"Seed: {config.seed}")
        print("-"*60)

    # Run test
    summary = asyncio.run(run_test(config))

    # Output results
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_summary(summary)
        passed = check_exit_criteria(summary, args.mode)

        if passed:
            print("\n✓ TEST PASSED")
        else:
            print("\n✗ TEST FAILED")

    # Save results if output specified
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        summary_path = args.output / f"mcp_test_{args.mode}_{timestamp}.json"

        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        if not args.json:
            print(f"\nResults saved to: {summary_path}")

    # Exit with appropriate code
    if not args.json:
        passed = check_exit_criteria(summary, args.mode)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

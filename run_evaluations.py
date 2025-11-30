#!/usr/bin/env python3
"""
Run evaluations for TabSage agents

Based on Day 4b: Agent Evaluation
"""

import asyncio
import argparse

from evaluation.runner import run_evaluations
from evaluation.regression import detect_regression, save_baseline
from observability.setup import initialize_observability

# Initialize observability
initialize_observability(
    enable_logging=True,
    enable_tracing=False,  # Tracing not needed for evaluation
    enable_metrics=False   # Metrics not needed for evaluation
)


async def main():
    parser = argparse.ArgumentParser(description="Run TabSage agent evaluations")
    parser.add_argument(
        "--config",
        default="tests/evaluations/test_config.json",
        help="Path to test_config.json"
    )
    parser.add_argument(
        "--output",
        default="tests/evaluations/results.json",
        help="Path to save evaluation results"
    )
    parser.add_argument(
        "--baseline",
        default="tests/evaluations/baseline_results.json",
        help="Path to baseline results"
    )
    parser.add_argument(
        "--check-regression",
        action="store_true",
        help="Check for regression against baseline"
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current results as baseline"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("TabSage Agent Evaluation")
    print("=" * 60)
    print()
    
    print(f"Loading config: {args.config}")
    results = await run_evaluations(args.config, args.output)
    
    # Print results
    print()
    print("=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print()
    print(f"Total agents: {results['total_agents']}")
    print(f"Total tests: {results['total_tests']}")
    print(f"Passed: {results['total_passed']}")
    print(f"Failed: {results['total_failed']}")
    print(f"Pass rate: {results['overall_pass_rate']:.2%}")
    print()
    
    # Details by agent
    for agent_name, agent_result in results['results'].items():
        print(f"  {agent_name}:")
        print(f"    Tests: {agent_result['total_tests']}")
        print(f"    Passed: {agent_result['passed']}/{agent_result['total_tests']}")
        print(f"    Pass rate: {agent_result['pass_rate']:.2%}")
        print()
    
    # Regression check
    if args.check_regression:
        print("=" * 60)
        print("REGRESSION DETECTION")
        print("=" * 60)
        print()
        
        regression_result = detect_regression(
            args.output,
            args.baseline
        )
        
        if regression_result.get("has_regression"):
            print("REGRESSION DETECTED!")
            print(f"   Regressed agents: {', '.join(regression_result['regressed_agents'])}")
            print()
            for agent_name, comparison in regression_result.get("comparisons", {}).items():
                if comparison.get("regression"):
                    print(f"   {agent_name}:")
                    for detail in comparison.get("regression_details", []):
                        print(f"     - {detail}")
        else:
            print("No regression detected")
        print()
    
    if args.save_baseline:
        save_baseline(args.output, args.baseline)
        print(f"Baseline saved to {args.baseline}")
        print()
    
    print("=" * 60)
    print("Evaluation complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


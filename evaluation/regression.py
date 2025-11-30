"""
Regression detection for TabSage evaluations

Based on Day 4b: Agent Evaluation
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from observability.logging import get_logger

logger = get_logger(__name__)


def load_baseline(baseline_path: str) -> Dict[str, Any]:
    """Loads baseline results
    
    Args:
        baseline_path: Path to baseline_results.json
        
    Returns:
        Dictionary with baseline results
    """
    if not Path(baseline_path).exists():
        logger.warning(f"Baseline file not found: {baseline_path}")
        return {}
    
    with open(baseline_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_results(
    current_results: Dict[str, Any],
    baseline_results: Dict[str, Any],
    thresholds: Dict[str, float]
) -> Dict[str, Any]:
    """Compares current results with baseline
    
    Args:
        current_results: Current evaluation results
        baseline_results: Baseline results
        thresholds: Metric thresholds (factuality, coherence, relevance)
        
    Returns:
        Dictionary with comparison results
    """
    comparisons = {}
    regressions = []
    
    for agent_name, current_result in current_results.get("results", {}).items():
        baseline_result = baseline_results.get("results", {}).get(agent_name)
        
        if not baseline_result:
            logger.warning(f"No baseline for agent: {agent_name}")
            continue
        
        comparison = {
            "agent": agent_name,
            "current_pass_rate": current_result.get("pass_rate", 0.0),
            "baseline_pass_rate": baseline_result.get("pass_rate", 0.0),
            "regression": False,
            "regression_details": []
        }
        
        # Check for regression by pass rate
        pass_rate_diff = current_result.get("pass_rate", 0.0) - baseline_result.get("pass_rate", 0.0)
        if pass_rate_diff < -0.1:  # Drop of more than 10%
            comparison["regression"] = True
            comparison["regression_details"].append(
                f"Pass rate dropped from {baseline_result.get('pass_rate', 0.0):.2%} to {current_result.get('pass_rate', 0.0):.2%}"
            )
        
        for metric in thresholds.keys():
            # Here can add more detailed metric comparison
            # For now check overall pass rate
            pass
        
        comparisons[agent_name] = comparison
        
        if comparison["regression"]:
            regressions.append(agent_name)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "has_regression": len(regressions) > 0,
        "regressed_agents": regressions,
        "comparisons": comparisons
    }


def detect_regression(
    current_results_path: str,
    baseline_path: str,
    thresholds: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Detects regression in evaluation results
    
    Args:
        current_results_path: Path to current results
        baseline_path: Path to baseline results
        thresholds: Metric thresholds (optional)
        
    Returns:
        Dictionary with regression detection results
    """
    if thresholds is None:
        thresholds = {
            "factuality": 0.8,
            "coherence": 0.8,
            "relevance": 0.8
        }
    
    with open(current_results_path, 'r', encoding='utf-8') as f:
        current_results = json.load(f)
    
    baseline_results = load_baseline(baseline_path)
    
    if not baseline_results:
        logger.warning("No baseline found, skipping regression detection")
        return {
            "has_regression": False,
            "message": "No baseline available"
        }
    
    # Compare results
    comparison = compare_results(current_results, baseline_results, thresholds)
    
    if comparison["has_regression"]:
        logger.error("Regression detected!", extra={
            "event_type": "regression_detected",
            "regressed_agents": comparison["regressed_agents"]
        })
    else:
        logger.info("No regression detected", extra={
            "event_type": "regression_check",
            "status": "pass"
        })
    
    return comparison


def save_baseline(results_path: str, baseline_path: str) -> None:
    """Saves current results as baseline
    
    Args:
        results_path: Path to current results
        baseline_path: Path to save baseline
    """
    import shutil
    
    shutil.copy(results_path, baseline_path)
    logger.info(f"Baseline saved to {baseline_path}", extra={
        "event_type": "baseline_saved",
        "baseline_path": baseline_path
    })


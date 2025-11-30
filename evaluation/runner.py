"""
Evaluation runner for TabSage agents

Based on Day 4b: Agent Evaluation
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from google.adk.evaluation import run_evaluations as adk_run_evaluations
    HAS_ADK_EVAL = True
except ImportError:
    HAS_ADK_EVAL = False

from observability.logging import get_logger

# Agent imports - make lazy to avoid circular dependencies
def get_agent_run_once(agent_name: str):
    """Lazy agent import"""
    if agent_name == "ingest_agent":
        from agents.ingest_agent import run_once
        return run_once
    elif agent_name == "kg_builder_agent":
        from agents.kg_builder_agent import run_once
        return run_once
    elif agent_name == "summary_agent":
        from agents.summary_agent import run_once
        return run_once
    elif agent_name == "intent_agent":
        from agents.intent_agent import recognize_intent
        return recognize_intent
    else:
        raise ValueError(f"Unknown agent: {agent_name}")

logger = get_logger(__name__)


def load_test_config(config_path: str) -> Dict[str, Any]:
    """Loads evaluation configuration
    
    Args:
        config_path: Path to test_config.json
        
    Returns:
        Dictionary with configuration
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_test_cases(test_file: str) -> List[Dict[str, Any]]:
    """Loads test cases from file
    
    Args:
        test_file: Path to *.test.json file
        
    Returns:
        List of test cases
    """
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("test_cases", [])


async def evaluate_agent(
    agent_name: str,
    test_cases: List[Dict[str, Any]],
    evaluators: List[str]
) -> Dict[str, Any]:
    """Runs evaluation for one agent
    
    Args:
        agent_name: Agent name
        test_cases: List of test cases
        evaluators: List of evaluators to use
        
    Returns:
        Dictionary with evaluation results
    """
    results = []
    
    for test_case in test_cases:
        case_name = test_case.get("name", "unnamed")
        input_data = test_case.get("input", {})
        expected = test_case.get("expected_output", {})
        
        logger.info(f"Running test case: {case_name}", extra={
            "event_type": "evaluation_test_start",
            "agent": agent_name,
            "test_case": case_name
        })
        
        try:
            # Get agent function
            agent_func = get_agent_run_once(agent_name)
            
            # Execute agent with correct parameters
            if agent_name == "summary_agent":
                result = await agent_func(
                    article_text=input_data.get("article_text", ""),
                    title=input_data.get("title", ""),
                    url=input_data.get("url", "")
                )
            elif agent_name == "intent_agent":
                result = await agent_func(input_data.get("user_message", ""))
            else:
                result = await agent_func(input_data)
            
            evaluation_result = {
                "test_case": case_name,
                "status": "success",
                "result": result,
                "expected": expected,
                "passed": True,
                "errors": []
            }
            
            # Validate results
            if agent_name == "ingest_agent":
                if expected.get("language"):
                    if result.get("language") != expected["language"]:
                        evaluation_result["passed"] = False
                        evaluation_result["errors"].append(
                            f"Language mismatch: expected {expected['language']}, got {result.get('language')}"
                        )
                
                chunks_count = len(result.get("chunks", []))
                if expected.get("chunks_count"):
                    min_chunks = expected["chunks_count"].get("min", 0)
                    max_chunks = expected["chunks_count"].get("max", 999)
                    if not (min_chunks <= chunks_count <= max_chunks):
                        evaluation_result["passed"] = False
                        evaluation_result["errors"].append(
                            f"Chunks count out of range: expected {min_chunks}-{max_chunks}, got {chunks_count}"
                        )
            
            elif agent_name == "kg_builder_agent":
                entities_count = len(result.get("entities", []))
                if expected.get("entities_count"):
                    min_entities = expected["entities_count"].get("min", 0)
                    if entities_count < min_entities:
                        evaluation_result["passed"] = False
                        evaluation_result["errors"].append(
                            f"Entities count too low: expected at least {min_entities}, got {entities_count}"
                        )
            
            elif agent_name == "summary_agent":
                if expected.get("has_summary") and not result.get("summary"):
                    evaluation_result["passed"] = False
                    evaluation_result["errors"].append("Missing summary")
                
                key_points_count = len(result.get("key_points", []))
                if expected.get("key_points_count"):
                    min_points = expected["key_points_count"].get("min", 0)
                    if key_points_count < min_points:
                        evaluation_result["passed"] = False
                        evaluation_result["errors"].append(
                            f"Key points count too low: expected at least {min_points}, got {key_points_count}"
                        )
            
            elif agent_name == "intent_agent":
                expected_intent = expected.get("intent")
                actual_intent = result.get("intent")
                if expected_intent and actual_intent != expected_intent:
                    evaluation_result["passed"] = False
                    evaluation_result["errors"].append(
                        f"Intent mismatch: expected {expected_intent}, got {actual_intent}"
                    )
            
            results.append(evaluation_result)
            
            if evaluation_result["passed"]:
                logger.info(f"Test case passed: {case_name}", extra={
                    "event_type": "evaluation_test_pass",
                    "agent": agent_name,
                    "test_case": case_name
                })
            else:
                logger.warning(f"Test case failed: {case_name}", extra={
                    "event_type": "evaluation_test_fail",
                    "agent": agent_name,
                    "test_case": case_name,
                    "errors": evaluation_result["errors"]
                })
        
        except Exception as e:
            logger.error(f"Test case error: {case_name}", extra={
                "event_type": "evaluation_test_error",
                "agent": agent_name,
                "test_case": case_name,
                "error": str(e)
            }, exc_info=True)
            
            results.append({
                "test_case": case_name,
                "status": "error",
                "error": str(e),
                "passed": False
            })
    
    total = len(results)
    passed = sum(1 for r in results if r.get("passed", False))
    failed = total - passed
    
    return {
        "agent": agent_name,
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total > 0 else 0.0,
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }


async def run_evaluations(
    config_path: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Runs all evaluations according to configuration
    
    Args:
        config_path: Path to test_config.json
        output_path: Path to save results (optional)
        
    Returns:
        Dictionary with all evaluation results
    """
    logger.info("Starting evaluations", extra={
        "event_type": "evaluation_start",
        "config_path": config_path
    })
    
    config = load_test_config(config_path)
    evaluations = config.get("evaluations", [])
    base_dir = Path(config_path).parent
    
    all_results = {}
    
    for eval_config in evaluations:
        agent_name = eval_config.get("agent")
        test_file = eval_config.get("test_file")
        evaluators = eval_config.get("evaluators", [])
        
        if not agent_name or not test_file:
            logger.warning(f"Skipping invalid evaluation config: {eval_config}")
            continue
        
        test_file_path = base_dir / test_file
        
        if not test_file_path.exists():
            logger.warning(f"Test file not found: {test_file_path}")
            continue
        
        test_cases = load_test_cases(str(test_file_path))
        
        # Execute evaluation
        result = await evaluate_agent(agent_name, test_cases, evaluators)
        all_results[agent_name] = result
    
    # Overall statistics
    total_tests = sum(r["total_tests"] for r in all_results.values())
    total_passed = sum(r["passed"] for r in all_results.values())
    total_failed = sum(r["failed"] for r in all_results.values())
    
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_agents": len(all_results),
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "overall_pass_rate": total_passed / total_tests if total_tests > 0 else 0.0,
        "results": all_results
    }
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {output_path}")
    
    logger.info("Evaluations completed", extra={
        "event_type": "evaluation_complete",
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed
    })
    
    return summary


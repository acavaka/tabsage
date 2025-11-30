#!/usr/bin/env python3
"""
Script to collect and display TabSage performance metrics

Usage:
    python scripts/collect_metrics.py [--endpoint http://localhost:8000/metrics]
"""

import argparse
import requests
import re
from typing import Dict, List, Tuple
from collections import defaultdict


def fetch_metrics(endpoint: str = "http://localhost:8000/metrics") -> str:
    """Fetch metrics from Prometheus endpoint.
    
    Args:
        endpoint: Metrics endpoint URL
        
    Returns:
        Metrics text
    """
    try:
        response = requests.get(endpoint, timeout=5)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return ""


def parse_metrics(metrics_text: str) -> Dict[str, List[Tuple[Dict[str, str], float]]]:
    """Parse Prometheus metrics text.
    
    Args:
        metrics_text: Raw metrics text
        
    Returns:
        Dictionary mapping metric names to list of (labels, value) tuples
    """
    metrics = defaultdict(list)
    
    # Pattern to match Prometheus metrics
    # Format: metric_name{label1="value1",label2="value2"} value
    pattern = r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^}]*)\}\s+([0-9.]+)'
    
    for line in metrics_text.split('\n'):
        if line.startswith('#') or not line.strip():
            continue
        
        match = re.match(pattern, line)
        if match:
            metric_name = match.group(1)
            labels_str = match.group(2)
            value = float(match.group(3))
            
            # Parse labels
            labels = {}
            if labels_str:
                label_pattern = r'(\w+)="([^"]*)"'
                for label_match in re.finditer(label_pattern, labels_str):
                    labels[label_match.group(1)] = label_match.group(2)
            
            metrics[metric_name].append((labels, value))
    
    return dict(metrics)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string
    """
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def display_agent_metrics(metrics: Dict[str, List[Tuple[Dict[str, str], float]]]):
    """Display agent performance metrics.
    
    Args:
        metrics: Parsed metrics dictionary
    """
    print("=" * 70)
    print("AGENT PERFORMANCE METRICS")
    print("=" * 70)
    print()
    
    # Agent requests
    if 'tabsage_agent_requests_total' in metrics:
        print("Agent Requests:")
        agent_requests = defaultdict(lambda: {'success': 0, 'error': 0, 'started': 0})
        
        for labels, value in metrics['tabsage_agent_requests_total']:
            agent_name = labels.get('agent_name', 'unknown')
            status = labels.get('status', 'unknown')
            if status == 'success':
                agent_requests[agent_name]['success'] = int(value)
            elif status == 'error':
                agent_requests[agent_name]['error'] = int(value)
            elif status == 'started':
                agent_requests[agent_name]['started'] = int(value)
        
        for agent_name, counts in sorted(agent_requests.items()):
            total = counts['success'] + counts['error']
            if total > 0:
                success_rate = (counts['success'] / total) * 100
                print(f"  {agent_name}:")
                print(f"    Total: {total}")
                print(f"    Success: {counts['success']} ({success_rate:.1f}%)")
                print(f"    Errors: {counts['error']}")
        print()
    
    # Agent duration
    if 'tabsage_agent_duration_seconds' in metrics:
        print("Agent Execution Time (P50, P95, P99):")
        agent_durations = defaultdict(list)
        
        for labels, value in metrics['tabsage_agent_duration_seconds']:
            agent_name = labels.get('agent_name', 'unknown')
            agent_durations[agent_name].append(value)
        
        for agent_name, durations in sorted(agent_durations.items()):
            if durations:
                durations.sort()
                p50 = durations[int(len(durations) * 0.5)]
                p95 = durations[int(len(durations) * 0.95)] if len(durations) > 1 else durations[-1]
                p99 = durations[int(len(durations) * 0.99)] if len(durations) > 1 else durations[-1]
                avg = sum(durations) / len(durations)
                
                print(f"  {agent_name}:")
                print(f"    Average: {format_duration(avg)}")
                print(f"    P50: {format_duration(p50)}")
                print(f"    P95: {format_duration(p95)}")
                print(f"    P99: {format_duration(p99)}")
        print()


def display_llm_metrics(metrics: Dict[str, List[Tuple[Dict[str, str], float]]]):
    """Display LLM performance metrics.
    
    Args:
        metrics: Parsed metrics dictionary
    """
    print("=" * 70)
    print("LLM PERFORMANCE METRICS")
    print("=" * 70)
    print()
    
    # LLM requests
    if 'tabsage_llm_requests_total' in metrics:
        print("LLM Requests by Agent:")
        llm_requests = defaultdict(int)
        
        for labels, value in metrics['tabsage_llm_requests_total']:
            agent_name = labels.get('agent_name', 'unknown')
            llm_requests[agent_name] += int(value)
        
        for agent_name, count in sorted(llm_requests.items()):
            print(f"  {agent_name}: {count} requests")
        print()
    
    # LLM tokens
    if 'tabsage_llm_tokens_total' in metrics:
        print("LLM Token Usage:")
        token_usage = defaultdict(lambda: {'input': 0, 'output': 0})
        
        for labels, value in metrics['tabsage_llm_tokens_total']:
            agent_name = labels.get('agent_name', 'unknown')
            token_type = labels.get('type', 'unknown')
            token_usage[agent_name][token_type] += int(value)
        
        total_input = 0
        total_output = 0
        
        for agent_name, tokens in sorted(token_usage.items()):
            input_tokens = tokens.get('input', 0)
            output_tokens = tokens.get('output', 0)
            total = input_tokens + output_tokens
            total_input += input_tokens
            total_output += output_tokens
            
            if total > 0:
                print(f"  {agent_name}:")
                print(f"    Input: {input_tokens:,} tokens")
                print(f"    Output: {output_tokens:,} tokens")
                print(f"    Total: {total:,} tokens")
        
        print()
        print(f"  Total Input: {total_input:,} tokens")
        print(f"  Total Output: {total_output:,} tokens")
        print(f"  Grand Total: {total_input + total_output:,} tokens")
        print()


def display_system_metrics(metrics: Dict[str, List[Tuple[Dict[str, str], float]]]):
    """Display system metrics.
    
    Args:
        metrics: Parsed metrics dictionary
    """
    print("=" * 70)
    print("SYSTEM METRICS")
    print("=" * 70)
    print()
    
    # Articles processed
    if 'tabsage_articles_processed_total' in metrics:
        print("Articles Processed:")
        articles = defaultdict(int)
        
        for labels, value in metrics['tabsage_articles_processed_total']:
            status = labels.get('status', 'unknown')
            articles[status] += int(value)
        
        for status, count in sorted(articles.items()):
            print(f"  {status}: {count}")
        print()
    
    # Active sessions
    if 'tabsage_active_sessions' in metrics:
        for labels, value in metrics['tabsage_active_sessions']:
            print(f"Active Sessions: {int(value)}")
        print()
    
    # KG entities
    if 'tabsage_kg_entities_total' in metrics:
        print("Knowledge Graph Entities:")
        entities = defaultdict(int)
        
        for labels, value in metrics['tabsage_kg_entities_total']:
            entity_type = labels.get('entity_type', 'unknown')
            entities[entity_type] += int(value)
        
        total = sum(entities.values())
        for entity_type, count in sorted(entities.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {entity_type}: {count} ({percentage:.1f}%)")
        print(f"  Total: {total}")
        print()
    
    # KG relations
    if 'tabsage_kg_relations_total' in metrics:
        print("Knowledge Graph Relations:")
        relations = defaultdict(int)
        
        for labels, value in metrics['tabsage_kg_relations_total']:
            relation_type = labels.get('relation_type', 'unknown')
            relations[relation_type] += int(value)
        
        total = sum(relations.values())
        for relation_type, count in sorted(relations.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {relation_type}: {count} ({percentage:.1f}%)")
        print(f"  Total: {total}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Collect and display TabSage performance metrics")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000/metrics",
        help="Prometheus metrics endpoint URL"
    )
    
    args = parser.parse_args()
    
    print("Fetching metrics from", args.endpoint)
    print()
    
    metrics_text = fetch_metrics(args.endpoint)
    
    if not metrics_text:
        print("No metrics available. Make sure:")
        print("  1. Metrics server is running (port 8000)")
        print("  2. Endpoint is correct")
        print("  3. Service is accessible")
        return
    
    metrics = parse_metrics(metrics_text)
    
    if not metrics:
        print("No metrics found in response")
        return
    
    display_agent_metrics(metrics)
    display_llm_metrics(metrics)
    display_system_metrics(metrics)
    
    print("=" * 70)
    print("Metrics collection complete")
    print("=" * 70)


if __name__ == "__main__":
    main()


# Evaluation Framework Guide for TabSage

> Complete evaluation setup based on Day 4b course

## Components

1. **Test sets (`*.test.json`)** - test cases for each agent
2. **Evaluation configuration (`test_config.json`)** - evaluation settings
3. **ADK evaluation integration** - using ADK evaluation framework
4. **Regression detection** - detecting performance regressions

---

## Quick Start

### 1. File Structure

```
tests/evaluations/
├── test_config.json          # Main configuration
├── ingest_agent.test.json     # Tests for Ingest Agent
├── kg_builder_agent.test.json # Tests for KG Builder Agent
├── summary_agent.test.json   # Tests for Summary Agent
├── intent_agent.test.json     # Tests for Intent Agent
├── results.json               # Evaluation results
└── baseline_results.json      # Baseline for regression detection
```

### 2. Run Evaluations

```bash
# Basic run
python3 run_evaluations.py

# With regression check
python3 run_evaluations.py --check-regression

# Save baseline
python3 run_evaluations.py --save-baseline

# All options
python3 run_evaluations.py \
    --config tests/evaluations/test_config.json \
    --output tests/evaluations/results.json \
    --baseline tests/evaluations/baseline_results.json \
    --check-regression \
    --save-baseline
```

---

## Test File Format

### `*.test.json` Structure

```json
{
  "test_cases": [
    {
      "name": "test_case_name",
      "input": {
        // Input data for agent
      },
      "expected_output": {
        // Expected results
      },
      "evaluators": ["factuality", "coherence", "relevance"]
    }
  ]
}
```

### Example: `ingest_agent.test.json`

```json
{
  "test_cases": [
    {
      "name": "basic_text_ingest",
      "input": {
        "raw_text": "Article text...",
        "metadata": {"url": "https://example.com"},
        "session_id": "test_session",
        "episode_id": "test_episode"
      },
      "expected_output": {
        "language": "en",
        "chunks_count": {"min": 1, "max": 5},
        "has_title": true
      },
      "evaluators": ["factuality", "coherence"]
    }
  ]
}
```

---

## Configuration (`test_config.json`)

```json
{
  "evaluations": [
    {
      "agent": "ingest_agent",
      "test_file": "ingest_agent.test.json",
      "evaluators": ["factuality", "coherence", "relevance"],
      "description": "Evaluation for Ingest Agent"
    }
  ],
  "global_settings": {
    "app_name": "tabsage",
    "model": "gemini-2.5-flash-lite",
    "timeout_seconds": 60
  },
  "regression_detection": {
    "enabled": true,
    "baseline_file": "baseline_results.json",
    "thresholds": {
      "factuality": 0.8,
      "coherence": 0.8,
      "relevance": 0.8
    }
  }
}
```

---

## Regression Detection

### How It Works

1. **Baseline** - results from first successful evaluation are saved
2. **Comparison** - current results are compared with baseline
3. **Detection** - if metrics fall below threshold, regression is registered

### Usage

```bash
# Save baseline
python3 run_evaluations.py --save-baseline

# Check regression
python3 run_evaluations.py --check-regression
```

### Regression Thresholds

Configured in `test_config.json`:

```json
{
  "regression_detection": {
    "thresholds": {
      "factuality": 0.8,  // Minimum 80%
      "coherence": 0.8,
      "relevance": 0.8
    }
  }
}
```

---

## Evaluation Results

### Result Format

```json
{
  "timestamp": "2025-11-29T...",
  "total_agents": 4,
  "total_tests": 10,
  "total_passed": 8,
  "total_failed": 2,
  "overall_pass_rate": 0.8,
  "results": {
    "ingest_agent": {
      "agent": "ingest_agent",
      "total_tests": 3,
      "passed": 3,
      "failed": 0,
      "pass_rate": 1.0,
      "results": [...]
    }
  }
}
```

### Interpretation

- **pass_rate >= 0.9** - excellent
- **pass_rate >= 0.8** - good
- **pass_rate >= 0.7** - acceptable
- **pass_rate < 0.7** - needs attention

---

## ADK Evaluation Integration

### Using ADK Evaluation Framework

```python
from google.adk.evaluation import run_evaluations as adk_run_evaluations

# Run via ADK
results = await adk_run_evaluations(
    test_config_path="tests/evaluations/test_config.json",
    agent=my_agent
)
```

### Requirements

- All agents must use `app_name="tabsage"`
- Test files must be in `*.test.json` format
- Configuration must match ADK format

---

## Evaluation Metrics

### Available Evaluators

1. **factuality** - factual accuracy
2. **coherence** - coherence and logic
3. **relevance** - result relevance

### Adding New Evaluators

```python
# In evaluation/runner.py
def evaluate_factuality(result: Dict, expected: Dict) -> float:
    # Your evaluation logic
    return score
```

---

## 🐛 Troubleshooting

### Tests Not Running

```bash
# Check configuration
python3 -c "from tabsage.evaluation.runner import load_test_config; print(load_test_config('tests/evaluations/test_config.json'))"
```

### Regression Not Detected

```bash
# Make sure baseline exists
ls -la tests/evaluations/baseline_results.json

# Check thresholds in test_config.json
```

### Test Errors

```bash
# Run with verbose logging
python3 run_evaluations.py --config tests/evaluations/test_config.json 2>&1 | grep ERROR
```

---

## 📚 Additional Resources

- [ADK Evaluation Documentation](https://google.github.io/adk-docs/)
- [Day 4b Notebook](../Practice/day-4b-agent-evaluation.ipynb)

---

**Last updated:** 2025-11-29


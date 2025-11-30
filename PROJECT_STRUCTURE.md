# TabSage Project Structure

## For Capstone Project

### Main Files (project root):

```
tabsage/
├── README.md                    # Main documentation (REQUIRED!)
├── PROJECT_STRUCTURE.md         # Project structure
│
├── pyproject.toml               # Project dependencies
├── pytest.ini                   # Test configuration
├── .gitignore                   # Ignored files
│
├── run_bot.py                   # Telegram bot launcher
├── run_web.py                   # Web interface launcher
├── run_evaluations.py           # Evaluation launcher
├── run_with_observability.py    # Launcher with observability
├── run_tests.sh                 # Test script
│
├── agents/                      # Agents (21 files)
│   ├── ingest_agent.py         # Ingest Agent
│   ├── kg_builder_agent.py     # KG Builder Agent
│   ├── summary_agent.py        # Summary Agent
│   └── ...                     # Other agents
│
├── tools/                       # Agent tools (14 files)
│   ├── kg_client.py            # Knowledge Graph client
│   ├── web_scraper.py          # Web scraper
│   ├── nlp.py                  # NLP utilities
│   └── ...                     # Other tools
│
├── storage/                     # Storage (2 files)
│   └── firestore_kg.py         # Firestore Knowledge Graph
│
├── schemas/                     # Pydantic models (2 files)
│   └── models.py                # Data models
│
├── services/                     # Services
│   ├── a2a/                    # A2A servers (9 files)
│   ├── bot/                    # Telegram bot (2 files)
│   └── web/                     # Web interface (3 files)
│
├── core/                        # System core (3 files)
│   ├── config.py               # Configuration
│   ├── orchestrator.py         # Orchestrator
│   └── orchestrator_a2a.py     # A2A Orchestrator
│
├── observability/               # Observability (6 files)
│   ├── logging.py              # Structured logging
│   ├── tracing.py              # OpenTelemetry tracing
│   └── metrics.py              # Prometheus metrics
│
├── memory/                      # Memory management (4 files)
│   ├── shared_memory.py        # Shared memory
│   └── firestore_memory.py     # Firestore memory
│
├── workflows/                   # Resumable workflows (2 files)
│   └── resumable.py            # Resumable workflow
│
├── registry/                     # A2A Registry (3 files)
│   └── vertex_ai_registry.py    # Vertex AI Registry
│
├── search/                      # Vertex AI Search (2 files)
│   └── vertex_ai_search.py     # Search implementation
│
├── evaluation/                   # Evaluation framework (3 files)
│   └── runner.py               # Evaluation runner
│
└── evaluators/                  # Evaluators (3 files)
    └── text_evaluator.py       # Text evaluator
│
├── tests/                       # Unit tests
│   ├── agents/                  # Agent tests
│   ├── tools/                   # Tool tests
│   ├── storage/                 # Storage tests
│   └── evaluations/             # Test sets for evaluation
│
├── scripts/                     # Useful scripts
│   ├── reprocess_articles.py    # Article reprocessing
│   ├── generate_podcast_all.py  # Audio generation from all articles
│   └── ...
│
├── examples/                    # Usage examples
│   ├── quick_start.py           # Quick start
│   ├── full_pipeline_example.py # Full pipeline
│   └── ...
│
├── docs/                        # Usage guides
│   ├── A2A_REGISTRY_GUIDE.md
│   ├── MEMORY_AND_WORKFLOWS_GUIDE.md
│   ├── EVALUATION_GUIDE.md
│   └── OBSERVABILITY_GUIDE.md
│
└── archive/                     # Old/outdated files
    └── README.md                # Archive description
```

---

## Key Components for Capstone:

### 1. Multi-Agent System
- 11 agents (Ingest, KG Builder, Summary, Intent, Topic Discovery, Scriptwriter, Guest, Audio Producer, Publisher, Evaluator, Editor, Orchestrator)
- Sequential, parallel, loop agents
- A2A communication

### 2. Tools
- 14+ custom tools
- Long-running operations
- Resumable workflows

### 3. Sessions & Memory
- Shared Memory between agents
- Firestore for long-term memory
- Context compaction

### 4. Observability
- Structured JSON logging
- OpenTelemetry tracing
- Prometheus metrics

### 5. Agent Evaluation
- Test sets (*.test.json)
- Evaluation runner
- Regression detection

### 6. A2A Protocol
- A2A Registry (Vertex AI + in-memory)
- Full integration of all agents

---

## Quick Start:

```bash
# 1. Install dependencies
pip install -r pyproject.toml

# 2. Set environment variables
export GOOGLE_API_KEY="your-key"
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export KG_PROVIDER="firestore"

# 3. Run bot
python run_bot.py

# 4. Run web interface
python run_web.py
```

---

## Documentation:

- **README.md** - main documentation with full description
- **PROJECT_STRUCTURE.md** - project structure
- **docs/** - detailed usage guides
  - `docs/INSTALL.md` - installation instructions
  - `docs/PODCAST_GENERATION.md` - audio generation documentation
  - `docs/REPROCESS_ARTICLES.md` - article reprocessing instructions
  - `docs/A2A_REGISTRY_GUIDE.md` - A2A Registry guide
  - `docs/MEMORY_AND_WORKFLOWS_GUIDE.md` - memory and workflows guide
  - `docs/EVALUATION_GUIDE.md` - evaluation guide
  - `docs/OBSERVABILITY_GUIDE.md` - observability guide
  - `docs/SCRIPTS_USAGE.md` - scripts documentation

---

## Project ready for:
- GitHub deployment
- Cloud Run deployment
- Capstone Project evaluation


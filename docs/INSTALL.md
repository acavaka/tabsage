# TabSage Installation

## Quick Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd tabsage

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install package in editable mode
pip install -e .

# 4. Verify installation
python3 -c "from core.config import get_config; print('Installation successful!')"
```

## What Does `pip install -e .` Do?

- Installs `tabsage` package in editable (development) mode
- All code changes are immediately available without reinstallation
- Packages available for import: `from agents import ...`, `from tools import ...`, `from core import ...`
- No need to add `sys.path.insert()` in every file

## Project Structure (Flat Layout)

The project uses **Flat Layout** structure, following best practices for agent projects:

- `agents/` - all agents
- `tools/` - agent tools
- `core/` - system core (config, orchestrator)
- `services/` - services (A2A, bot, web)
- `storage/`, `schemas/`, `observability/`, etc.

**Advantages:**
- Short imports: `from agents.ingest_agent import ...`
- Flat structure - easier navigation
- Follows best practices for agents

## Verify Installation

```bash
# Check that package is installed
pip list | grep tabsage

# Check imports
python3 -c "from agents.ingest_agent import run_once; print('OK')"
```

## Update After Changes

After code changes, the package is automatically updated (editable mode), but if you added new files/packages, you may need:

```bash
pip install -e . --force-reinstall
```


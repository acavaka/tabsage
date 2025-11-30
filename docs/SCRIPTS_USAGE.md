# 📜 TabSage Scripts Purpose and Usage

## Overview

Scripts in the `scripts/` directory are **command-line utilities** for managing and maintaining the TabSage project. They are **not imported** in the main code, but are run **manually** to perform administrative tasks.

---

## Script List and Purpose

### 1. `start_all_a2a_servers.py` — Start A2A Servers

**Purpose:** Starts all A2A (Agent-to-Agent) servers for distributed architecture operation.

**When to use:**
- During development and testing of A2A functionality
- To demonstrate distributed agent architecture
- Before running `examples/full_a2a_pipeline_example.py`

**Referenced in:**
- `examples/full_a2a_pipeline_example.py` — requires running servers
- `docs/A2A_REGISTRY_GUIDE.md` — A2A documentation
- `archive/README_A2A_FULL.md` — A2A documentation

**Usage:**
```bash
python scripts/start_all_a2a_servers.py
```

**Starts servers:**
- KG Builder (port 8002)
- Topic Discovery (port 8003)
- Scriptwriter (port 8004)
- Guest (port 8005)
- Audio Producer (port 8006)
- Evaluator (port 8007)
- Editor (port 8008)
- Publisher (port 8009)

---

### 2. `register_agents.py` — Register Agents in Vertex AI Registry

**Purpose:** Registers all TabSage agents in Vertex AI Agent Registry for centralized management.

**When to use:**
- When setting up production environment
- For integration with Vertex AI Agent Builder
- For centralized agent version management

**Referenced in:**
- `docs/A2A_REGISTRY_GUIDE.md` — main usage guide
- Vertex AI integration documentation

**Usage:**
```bash
python scripts/register_agents.py
```

**Registers agents:**
- kg_builder_agent
- topic_discovery_agent
- scriptwriter_agent
- guest_agent
- audio_producer_agent
- evaluator_agent
- editor_agent
- publisher_agent

---

### 3. `get_my_chat_id.py` — Get Telegram chat_id

**Purpose:** Helps get your Telegram chat_id for sending messages and files via bot.

**When to use:**
- During initial Telegram bot setup
- When you need to send audio file to user
- For notification setup

**Referenced in:**
- `scripts/send_audio_to_telegram.py` — references this script
- `scripts/generate_podcast_all.py` — mentions in hints

**Usage:**
```bash
python scripts/get_my_chat_id.py
```

**Process:**
1. Starts temporary Telegram bot
2. Waits for message from user
3. Shows chat_id
4. Stops

---

### 4. `send_audio_to_telegram.py` — Send Audio via Telegram

**Purpose:** Sends audio file (e.g., generated podcast) to user via Telegram bot.

**When to use:**
- After generating podcast via `generate_podcast_all.py`
- To send audio summaries to users
- For testing Telegram integration

**Referenced in:**
- `scripts/generate_podcast_all.py` — suggests using after generation
- `scripts/get_my_chat_id.py` — references in instructions

**Usage:**
```bash
# With chat_id from environment variable
export TELEGRAM_CHAT_ID=123456789
python scripts/send_audio_to_telegram.py audio_summary.mp3

# With chat_id as argument
python scripts/send_audio_to_telegram.py audio_summary.mp3 123456789
```

---

### 5. `generate_podcast_all.py` — Generate Podcast from All Articles

**Purpose:** Creates a single audio podcast combining information from all articles in Firestore.

**When to use:**
- To create final podcast from all processed articles
- For generating weekly/monthly summaries
- To demonstrate audio generation functionality

**Referenced in:**
- `PROJECT_STRUCTURE.md` — project structure description
- `CLEANUP_PLAN.md` — list of useful scripts
- `scripts/reprocess_articles.py` — mentions in hints

**Usage:**
```bash
export KG_PROVIDER=firestore
export GOOGLE_CLOUD_PROJECT=your-project-id
python scripts/generate_podcast_all.py
```

**Process:**
1. Gets all articles from Firestore
2. Generates podcast script via Scriptwriter Agent
3. Creates audio via Audio Producer Agent + Google Cloud TTS
4. Saves audio file

---

### 6. `reprocess_articles.py` — Reprocess Articles

**Purpose:** Reprocesses articles from Firestore to update knowledge graph with correct relationships.

**When to use:**
- After changes in agent processing logic
- To fix errors in existing data
- To update relationships between articles and entities
- During data migration

**Referenced in:**
- `REPROCESS_ARTICLES.md` — full usage documentation
- `PROJECT_STRUCTURE.md` — project structure description
- `CLEANUP_PLAN.md` — list of useful scripts
- `scripts/generate_podcast_all.py` — mentions in hints

**Usage:**
```bash
# Reprocess all articles
python scripts/reprocess_articles.py --all

# Reprocess specific URLs
python scripts/reprocess_articles.py --urls https://habr.com/... https://habr.com/...

# With project specification
python scripts/reprocess_articles.py --all --project-id your-project-id
```

**Process:**
1. Gets articles from Firestore (or specified URLs)
2. Downloads content via Web Scraper
3. Processes via Ingest → KG Builder → Summary pipeline
4. Updates entities and relationships with correct `article_url`
5. Updates article in Firestore

**Critical:** Saves `article_url` in entities and relationships, enabling visualization of relationships between articles.

---

## 🔄 Script Relationships

### Typical Workflows:

#### 1. A2A Environment Setup:
```bash
# 1. Start all A2A servers
python scripts/start_all_a2a_servers.py

# 2. (Optional) Register in Vertex AI Registry
python scripts/register_agents.py

# 3. Use in examples
python examples/full_a2a_pipeline_example.py
```

#### 2. Podcast Generation and Sending:
```bash
# 1. Generate podcast from all articles
python scripts/generate_podcast_all.py

# 2. Get chat_id (if needed)
python scripts/get_my_chat_id.py

# 3. Send audio
python scripts/send_audio_to_telegram.py audio_summary_*.mp3
```

#### 3. Firestore Data Update:
```bash
# 1. Reprocess articles to update graph
python scripts/reprocess_articles.py --all

# 2. Check statistics
python examples/view_kg_stats.py

# 3. Export graph
python examples/export_kg.py
```

---

## Usage in Project

### In Main Code:
**Scripts are NOT imported** in main project code (`src/tabsage/`)

### In Documentation:
**Referenced in:**
- `README.md` — general documentation
- `REPROCESS_ARTICLES.md` — reprocessing documentation
- `docs/A2A_REGISTRY_GUIDE.md` — A2A Registry guide
- `PROJECT_STRUCTURE.md` — project structure
- `CLEANUP_PLAN.md` — project cleanup plan

### In Examples:
**Used in:**
- `examples/full_a2a_pipeline_example.py` — requires running A2A servers

### In Other Scripts:
**Reference each other:**
- `get_my_chat_id.py` → `send_audio_to_telegram.py`
- `generate_podcast_all.py` → `send_audio_to_telegram.py`
- `generate_podcast_all.py` → `reprocess_articles.py`

---

## Script Role in Project

### For Development:
- **`start_all_a2a_servers.py`** — A2A architecture testing
- **`register_agents.py`** — Vertex AI integration setup

### For Administration:
- **`reprocess_articles.py`** — Firestore data updates
- **`generate_podcast_all.py`** — bulk content generation

### For Users:
- **`get_my_chat_id.py`** — Telegram integration setup
- **`send_audio_to_telegram.py`** — sending results to users

---

## Recommendations

### Required for Production:
- `reprocess_articles.py` — for data updates
- `register_agents.py` — for Vertex AI integration

### Useful for Development:
- `start_all_a2a_servers.py` — for A2A testing
- `get_my_chat_id.py` — for Telegram setup

### Optional:
- `generate_podcast_all.py` — for bulk generation
- `send_audio_to_telegram.py` — for sending results

---

## Summary

**Scripts are command-line utilities** that:
- Are not part of main code
- Are run manually for administrative tasks
- Help manage project and data
- Are used for system setup and maintenance
- Are documented in README and other documents

**They are needed for:**
1. Environment setup (A2A servers, Registry)
2. Data maintenance (article reprocessing)
3. Content generation (podcasts)
4. Integration with external services (Telegram)

**For project submission:** All scripts are important as they demonstrate:
- Project management
- Integration with external services
- Administrative capabilities
- Production-ready functionality


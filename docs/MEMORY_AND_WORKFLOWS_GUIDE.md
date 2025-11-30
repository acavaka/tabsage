# 🧠 Memory Management and Workflows Guide

> Implementation based on Day 3b (Memory) and Day 2b (Tools Best Practices)

## Components

### 1. Memory Management (Day 3b)

#### 1.1 Long-Term Memory via Firestore

**FirestoreMemoryService** - persistent storage for long-term memory.

```python
from tabsage.memory.firestore_memory import FirestoreMemoryService

# Initialization
memory_service = FirestoreMemoryService(project_id="YOUR_PROJECT_ID")

# Add session to memory
result = await memory_service.add_session_to_memory(
    app_name="tabsage",
    user_id="user_123",
    session_id="session_456"
)

# Search memory
results = await memory_service.search_memory(
    app_name="tabsage",
    user_id="user_123",
    query="microservices",
    limit=10
)

# Add article reference
memory_service.add_article_reference(
    article_id="article_123",
    article_data={
        "url": "https://habr.com/...",
        "title": "...",
        "summary": "...",
        "key_points": [...]
    }
)
```

**Firestore Structure:**
- `memory/` - consolidated facts and references
- `memory/facts/` - extracted facts from sessions
- `memory/articles/` - article references for quick access

#### 1.2 Shared Memory Between Agents

**SharedMemoryManager** - shared memory for data exchange between agents.

```python
from tabsage.memory.shared_memory import get_shared_memory

# Get global instance
shared_mem = get_shared_memory()

# Save data
shared_mem.set("ingest_result", result_data, namespace="pipeline_123")

# Get data
result = shared_mem.get("ingest_result", namespace="pipeline_123")

# Share data between agents
shared_mem.share_between_agents(
    from_agent="ingest_agent",
    to_agent="kg_builder_agent",
    data={"chunks": chunks, "title": title}
)

# Get all data from namespace
all_data = shared_mem.get_all(namespace="pipeline_123")
```

**Usage in Pipeline:**

```python
# In Ingest Agent
shared_mem = get_shared_memory()
shared_mem.set("ingested_data", {
    "chunks": chunks,
    "title": title,
    "language": language
}, namespace=f"session_{session_id}")

# In KG Builder Agent
shared_mem = get_shared_memory()
ingested_data = shared_mem.get("ingested_data", namespace=f"session_{session_id}")
```

#### 1.3 Context Compaction

**Context compression** for optimizing token usage.

```python
from tabsage.memory.context_compaction import compact_context, summarize_context

# Compress events
events = [...]  # List of events from session
compacted = compact_context(
    events,
    max_tokens=2000,
    preserve_recent=5  # Preserve last 5 events
)

# Create context summary
summary = summarize_context(events)
```

**Compression Strategy:**
- Preserves last N events completely
- Compresses old events, keeping only important ones (tool calls, final responses)
- Removes intermediate messages

---

### 2. Tools Best Practices (Day 2b)

#### 2.1 Long-Running Operations

**Operations with pause for human confirmation.**

```python
from tabsage.tools.long_running import process_large_article_batch, delete_article_from_kg
from google.adk.tools import ToolContext

# Process large article batch
def my_tool(urls: list[str], tool_context: ToolContext):
    return process_large_article_batch(urls, tool_context)

# Delete article with confirmation
def delete_tool(article_id: str, tool_context: ToolContext):
    return delete_article_from_kg(article_id, tool_context)
```

**How It Works:**

1. **First call:** Tool checks conditions (e.g., number of articles > 10)
2. **Request confirmation:** `tool_context.request_confirmation("Confirm operation?")`
3. **Pause:** Agent stops and waits for response
4. **Second call:** After confirmation, tool executes with result

**Example in Agent:**

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

agent = LlmAgent(
    name="article_processor",
    tools=[FunctionTool(func=process_large_article_batch)],
    instruction="Process articles. For large batches request confirmation."
)
```

#### 2.2 Resumable Workflows

**Resumable workflows for long-running operations.**

```python
from tabsage.workflows.resumable import ResumableWorkflow, create_article_processing_workflow

# Create workflow
workflow = await create_article_processing_workflow([
    "https://habr.com/ru/articles/519982/",
    "https://habr.com/ru/articles/658157/",
    # ... more URLs
])

# Execute
result = await workflow.execute()

# If workflow was paused, can resume
if workflow.status == WorkflowStatus.PAUSED:
    result = await workflow.resume()
```

**Creating Custom Workflow:**

```python
workflow = ResumableWorkflow(workflow_id="my_workflow")

# Add steps
async def step1(state: Dict[str, Any]) -> Dict[str, Any]:
    # Execute step 1
    state["step1_result"] = "done"
    return {"status": "completed"}

async def step2(state: Dict[str, Any]) -> Dict[str, Any]:
    # Step 2 depends on step 1
    result = state.get("step1_result")
    return {"status": "completed"}

workflow.add_step("download", step1)
workflow.add_step("process", step2, depends_on=[0])  # Depends on step 0

# Execute
result = await workflow.execute()
```

**Features:**

- **Auto-save:** State is saved to JSON file
- **Resume:** Can resume after pause
- **Dependencies:** Steps can depend on other steps
- **Error handling:** On error, workflow stops with state saved

---

## Agent Integration

### Memory Service Integration in Runner

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from tabsage.memory.firestore_memory import FirestoreMemoryService

# Create memory service
memory_service = FirestoreMemoryService()

# Create runner with memory
runner = Runner(
    agent=my_agent,
    app_name="tabsage",
    session_service=InMemorySessionService(),
    memory_service=memory_service  # Add memory service
)
```

### Using Shared Memory in Pipeline

```python
from tabsage.memory.shared_memory import get_shared_memory

async def process_article_pipeline(url: str):
    shared_mem = get_shared_memory()
    session_id = f"session_{hash(url)}"
    
    # Step 1: Ingest
    ingest_result = await ingest_agent.run_once({...})
    shared_mem.set("ingest_result", ingest_result, namespace=session_id)
    
    # Step 2: KG Builder (reads from shared memory)
    ingest_data = shared_mem.get("ingest_result", namespace=session_id)
    kg_result = await kg_builder_agent.run_once({
        "chunks": ingest_data["chunks"],
        ...
    })
    shared_mem.set("kg_result", kg_result, namespace=session_id)
    
    # Step 3: Summary
    summary_result = await summary_agent.run_once({...})
    
    # Cleanup after completion
    shared_mem.clear_namespace(session_id)
```

---

## Usage Examples

### Example 1: Article Processing with Confirmation

```python
from tabsage.tools.long_running import process_large_article_batch
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Create agent
agent = LlmAgent(
    name="batch_processor",
    tools=[FunctionTool(func=process_large_article_batch)],
    instruction="Process article batches. For large batches request confirmation."
)

# Usage
# Agent will automatically request confirmation if articles > 10
```

### Example 2: Resumable Workflow for Processing

```python
from tabsage.workflows.resumable import create_article_processing_workflow

urls = [
    "https://habr.com/ru/articles/519982/",
    "https://habr.com/ru/articles/658157/",
    # ... 20+ URLs
]

workflow = await create_article_processing_workflow(urls)

# Execution (may be paused)
result = await workflow.execute()

# If paused, can resume later
if workflow.status == WorkflowStatus.PAUSED:
    # ... user does something ...
    result = await workflow.resume()
```

---

## Configuration

### Firestore Memory Service

```bash
# Install dependencies
pip install google-cloud-firestore

# Configure authentication
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
```

### Shared Memory

By default uses in-memory storage. For production can be extended to Redis:

```python
# In shared_memory.py can add Redis backend
class RedisSharedMemoryManager(SharedMemoryManager):
    def __init__(self, redis_client):
        self.redis = redis_client
        # ... Redis implementation
```

---

## 📚 Additional Resources

- [ADK Memory Documentation](https://google.github.io/adk-docs/memory/)
- [ADK Tools Best Practices](https://google.github.io/adk-docs/tools/)
- [Day 3b Notebook](../Practice/day-3b-agent-memory.ipynb)
- [Day 2b Notebook](../Practice/day-2b-agent-tools-best-practices.ipynb)

---

**Last updated:** 2025-11-29


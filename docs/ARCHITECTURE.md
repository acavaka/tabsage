# TabSage Architecture

## System Overview

TabSage is a multi-agent system that processes articles and builds knowledge graphs. The architecture consists of 12 specialized agents working together through a coordinated pipeline.

## Complete System Architecture

For a complete overview of the entire system, see [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) with the full system diagram.

## Architecture Diagram

```mermaid
graph TB
    User[User via Telegram Bot] --> Intent[Intent Recognition Agent]
    
    Intent -->|URL| URLFlow[URL Processing Flow]
    Intent -->|Search| SearchFlow[Search Flow]
    Intent -->|Audio| AudioFlow[Audio Generation Flow]
    
    subgraph URLFlow[Article Processing Pipeline]
        URLFlow --> Scraper[Web Scraper Tool]
        Scraper --> Ingest[Ingest Agent]
        Ingest --> KG[KG Builder Agent]
        Ingest --> Summary[Summary Agent]
        KG --> Firestore[(Firestore Knowledge Graph)]
        Summary --> Firestore
    end
    
    subgraph SearchFlow[Search & Discovery]
        SearchFlow --> Topic[Topic Discovery Agent]
        Topic --> Guest[Guest Agent]
        Guest --> Firestore
    end
    
    subgraph AudioFlow[Audio Generation Pipeline]
        AudioFlow --> Scriptwriter[Scriptwriter Agent]
        Scriptwriter --> Audio[Audio Producer Agent]
        Audio --> Publisher[Publisher Agent]
        Scriptwriter --> Editor[Editor Agent]
        Editor --> Evaluator[Evaluator Agent]
    end
    
    Firestore --> Web[Web Interface]
    Firestore --> Search[Semantic Search]
    
    style User fill:#e1f5ff
    style Intent fill:#fff4e1
    style Ingest fill:#e8f5e9
    style KG fill:#e8f5e9
    style Summary fill:#e8f5e9
    style Firestore fill:#fff9c4
    style Web fill:#f3e5f5
```

## Agent Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant Intent as Intent Agent
    participant Scraper as Web Scraper
    participant Ingest as Ingest Agent
    participant KG as KG Builder Agent
    participant Summary as Summary Agent
    participant Firestore as Firestore KG
    participant Topic as Topic Discovery
    participant Scriptwriter as Scriptwriter
    participant Audio as Audio Producer
    
    User->>Intent: Send article URL
    Intent->>Scraper: Fetch article
    Scraper->>Ingest: Raw text + metadata
    
    par Parallel Processing
        Ingest->>KG: Chunks + title
        KG->>Firestore: Entities & Relations
    and
        Ingest->>Summary: Article text
        Summary->>Firestore: Summary
    end
    
    User->>Topic: Discover topics
    Topic->>Firestore: Query graph
    Firestore->>Topic: Graph snapshot
    Topic->>Scriptwriter: Topics + format
    Scriptwriter->>Audio: Script
    Audio->>User: Audio podcast
```

## Component Architecture

```mermaid
graph LR
    subgraph Agents[Agent Layer]
        A1[Ingest Agent]
        A2[KG Builder Agent]
        A3[Summary Agent]
        A4[Intent Agent]
        A5[Topic Discovery]
        A6[Scriptwriter]
        A7[Audio Producer]
        A8[Publisher]
        A9[Evaluator]
        A10[Editor]
        A11[Guest]
        A12[Orchestrator]
    end
    
    subgraph Tools[Tools Layer]
        T1[Web Scraper]
        T2[NLP Tools]
        T3[NER & Linking]
        T4[Embeddings]
        T5[TTS]
        T6[Audio Utils]
        T7[KG Client]
    end
    
    subgraph Storage[Storage Layer]
        S1[Firestore KG]
        S2[Firestore Memory]
        S3[Shared Memory]
    end
    
    subgraph Observability[Observability]
        O1[Structured Logging]
        O2[OpenTelemetry]
        O3[Prometheus]
    end
    
    subgraph Communication[Communication]
        C1[A2A Protocol]
        C2[Vertex AI Registry]
        C3[Remote Agents]
    end
    
    Agents --> Tools
    Agents --> Storage
    Agents --> Observability
    Agents --> Communication
    
    style Agents fill:#e8f5e9
    style Tools fill:#fff4e1
    style Storage fill:#e1f5ff
    style Observability fill:#f3e5f5
    style Communication fill:#fff9c4
```

## Data Flow

```mermaid
flowchart TD
    Start[Article URL] --> Scrape[Web Scraping]
    Scrape --> Normalize[Text Normalization]
    Normalize --> Chunk[Text Chunking]
    
    Chunk --> Extract[Entity Extraction]
    Extract --> Link[Entity Linking]
    Link --> Graph[Knowledge Graph]
    
    Chunk --> Summarize[Summary Generation]
    Summarize --> Graph
    
    Graph --> Discover[Topic Discovery]
    Discover --> Script[Script Generation]
    Script --> AudioGen[Audio Generation]
    AudioGen --> Publish[Publishing]
    
    Graph --> Search[Semantic Search]
    Graph --> Visualize[Web Visualization]
    
    style Start fill:#e1f5ff
    style Graph fill:#fff9c4
    style Visualize fill:#f3e5f5
```

## Key Concepts Implemented

### 1. Multi-Agent System
- **12 Specialized Agents**: Each agent has a specific role
- **Sequential Pipeline**: Ingest → KG Builder → Summary
- **Parallel Processing**: KG Builder processes chunks in parallel
- **Loop Agents**: Topic Discovery iterates to find topics
- **A2A Communication**: Agents communicate via standard protocol

### 2. Tools
- **Custom Tools**: 14+ specialized tools
- **Long-running Operations**: Pause/resume via workflows
- **Tool Integration**: Seamless integration with agents

### 3. Sessions & Memory
- **InMemorySessionService**: Session management
- **FirestoreMemoryService**: Long-term memory
- **Shared Memory**: Inter-agent communication
- **Context Compaction**: Efficient context management

### 4. Observability
- **Structured Logging**: JSON logs with context
- **OpenTelemetry Tracing**: Distributed tracing
- **Prometheus Metrics**: Performance metrics

### 5. Agent Evaluation
- **Test Sets**: Comprehensive test cases
- **Evaluation Runner**: Automated evaluation
- **Regression Detection**: Performance monitoring

### 6. A2A Protocol
- **A2A Registry**: Centralized agent registry
- **Remote Agents**: Distributed agent execution
- **Standard Interface**: Protocol-based communication


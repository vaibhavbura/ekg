# Engineering Knowledge Graph (EKG)

An Engineering Knowledge Graph (EKG) that ingests infrastructure configuration files and unifies them into a queryable graph.  
The system exposes a natural language interface that allows engineers to ask operational questions such as:

- Who owns the payment service?
- What breaks if Redis goes down?
- How does the API Gateway connect to the orders database?

This project demonstrates how graph databases and LLMs can be combined to reason over complex engineering systems.

---

<img width="3199" height="4437" alt="immmmj" src="https://github.com/user-attachments/assets/741cb44f-8060-41f5-9d0a-6e3bd66e2f6f" />


## Key Features

- Pluggable ingestion from infrastructure configuration files
- Unified graph model for services, databases, caches, and teams
- Deterministic graph queries for dependencies and blast radius
- LLM-powered natural language interface (intent routing only)
- One-command startup using Docker Compose

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Groq API key

---

### 1. Configure Environment Variables

Create a `.env` file in the project root:

```yaml
GROQ_API_KEY=your_api_key_here
```

Connect to Remote Neo4j (e.g., AuraDB)**

```yaml
NEO4J_URI=neo4j+s://<your-instance-id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
```

---

### 2. Database Setup

**Option A: Local Docker Instance (Default)**
The system automatically starts a local Neo4j container.
- **URL**: `bolt://localhost:7687`
- **User**: `neo4j`
- **Password**: `password` (Set in `docker-compose.yml`)
- **Action**: Just run `docker-compose up`, no extra setup needed.

**Option B: Neo4j AuraDB (Cloud)**
1. Create a free account at [Neo4j Aura](https://neo4j.com/cloud/aura/).
2. Create an instance and copy the credentials.
3. Update your `.env` file (as shown above).
4. Run the ingestion script locally to populate the cloud DB:
   ```bash
   # Windows
   $env:PYTHONPATH="."; python scripts/ingest_data.py
   
   # Linux/Mac
   PYTHONPATH=. python scripts/ingest_data.py
   ```

---

### 3. Start the System

```bash
docker-compose up --build
```

This will:
- Start Neo4j (graph database)
- Start the Streamlit application
- Wait for Neo4j to become healthy before launching the app

---

### 3. Access the UI

Open your browser at:
http://localhost:8501

---

### 4. Data Ingestion

- On first startup, the app detects an empty graph and automatically ingests data
- You can manually re-ingest data using the "Re-Ingest Data" button in the sidebar

---

## Architecture Overview

**Raw Config Files**
- `docker-compose.yml`
- `teams.yaml`
- `k8s-deployments.yaml` (optional)

**Connectors Layer**
- `DockerComposeConnector`
- `TeamsConnector`
- `KubernetesConnector` (optional)

**Graph Storage Layer**
- `Neo4j` (MERGE / upsert semantics)

**Logic Layer**
- `Query Engine` (deterministic graph traversal)
- `LLM Router` (intent classification only)

**UI Layer**
- `Streamlit` Chat Interface

---

## Core Components

### Connectors
Pluggable modules that parse raw configuration files and emit graph nodes and relationships.  
Each connector implements a shared `BaseConnector` interface and returns a standardized list of nodes and edges.

---

### Graph Storage
Neo4j stores the unified graph. Nodes represent services, databases, caches, and teams.  
Edges represent relationships such as `DEPENDS_ON`, `CALLS`, `USES`, and `OWNED_BY`.  
All writes use idempotent `MERGE` operations.

---

### Query Engine
A deterministic Python layer that executes Cypher queries for:
- Ownership lookup
- Upstream and downstream dependencies
- Blast radius analysis
- Shortest path between components

---

### LLM Router
Uses Groq (Llama 3.3 70B) to convert natural language into structured JSON intents.  
The LLM never queries Neo4j directly and cannot fabricate data.

---

### UI
A Streamlit-based chat interface that:
- Accepts natural language questions
- Displays structured results and summaries
- Handles database and ingestion errors gracefully

---

## Design Decisions

### Connector Pluggability
New data sources can be added by implementing the `BaseConnector` interface and registering the connector in the ingestion pipeline.

---

### Graph Updates
The graph is cleared and rebuilt during re-ingestion for correctness and simplicity.  
A production version could use incremental updates triggered by file watchers or APIs.

---

### Cycle Handling
Dependency cycles are handled safely using Neo4j variable-length traversals and distinct node collection, preventing infinite loops.

---

### Natural Language to Query Mapping
The LLM outputs a constrained JSON intent schema that maps directly to deterministic query functions, preventing hallucination.

---

### Failure Handling
- Unknown intents return a safe fallback response
- Empty graph results are explicitly reported
- Neo4j connection issues are surfaced in the UI

---

### Scale Considerations
At large scale, unbounded traversals and large result sets would be bottlenecks.  
Depth limits, pagination, caching, and incremental ingestion would be required.

---

### Why Neo4j
Neo4j was chosen for its native graph traversal capabilities, expressive Cypher queries, and suitability for dependency-driven systems.

---

## Tradeoffs and Limitations

- Static configuration files are treated as the source of truth
- No authentication or access control in the UI
- Full graph rebuilds instead of incremental diffs
- Dependency on LLM availability for intent routing

---

## Tech Stack

- Python 3.11
- Neo4j 5.15
- Streamlit
- Groq (Llama 3.3 70B)
- Docker & Docker Compose

---

## Directory Structure

- `connectors/`   - Ingestion logic
- `graph/`        - Neo4j storage and queries
- `chat/`         - LLM routing and context
- `ui/`           - Streamlit application
- `scripts/`      - Ingestion and validation utilities
- `data/`         - Sample configuration files

---

## AI Usage

AI was used to accelerate development, generate scaffolding, and explore design options.  
All AI-generated code and content were reviewed, validated, and corrected manually.

---

## Summary

This project demonstrates how LLMs and graph databases can be combined to create an extensible system for reasoning about engineering infrastructure while maintaining deterministic execution and explainability.

This project demonstrates how LLMs and graph databases can be combined to create an extensible system for reasoning about engineering infrastructure while maintaining deterministic execution and explainability.

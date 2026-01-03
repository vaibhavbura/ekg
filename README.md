# Engineering Knowledge Graph (EKG)

A unified graph system that ingests infrastructure definitions (`docker-compose.yml`, `k8s-deployments.yaml`, `teams.yaml`) and provides a Natural Language Interface to answer engineering questions like "What breaks if redis goes down?".

##  Quick Start

### Prerequisites
- Docker & Docker Compose
- Groq API Key

### Setup
1. **Set API Key**:
   Create a `.env` file in the root or export the variable:
   ```bash
   export GROQ_API_KEY=gsk_...
   ```
   *(Or edit `docker-compose.yml` to include it directly)*

2. **Start System**:
   ```bash
   docker-compose up --build
   ```
   This will:
   - Start Neo4j (Graph Database)
   - Start the Streamlit App
   - Wait for Neo4j to be ready

3. **Access UI**:
   Open [http://localhost:8501](http://localhost:8501)

4. **Ingest Data**:
   The app will auto-detect an empty graph and run ingestion. You can also click "Re-Ingest Data" in the sidebar.

## 🏗️ Architecture

```mermaid
graph TD
    Configs[Config Files] --> Connectors[Connectors]
    Connectors --> Storage[Graph Storage (Neo4j)]
    User[User] --> UI[Streamlit UI]
    UI --> Router[Chat Router (LLM)]
    Router --> Query[Query Engine]
    Query --> Storage
    Query --> UI
```

### Components
- **Connectors**: Pluggable modules (`docker_compose.py`, `teams.py`) that parse raw files into Nodes/Edges.
- **Graph Storage**: Neo4j database storing the unified graph.
- **Query Engine**: Deterministic Python execution of Cypher queries (Blast Radius, Pathfinding).
- **Chat Router**: LLM (GPT-4) classifies natural language into structured JSON intent (e.g., `blast_radius(node_id="redis")`).
- **UI**: Streamlit interface for chat and visualization.

## ❓ Design Decisions

**1. Connector Pluggability**
Connectors inherit from `BaseConnector` and return a standard list of Nodes/Edges. Adding Terraform support just requires implementing `TerraformConnector(BaseConnector)` and adding it to the `ingest_data.py` script.

**2. Graph Updates**
The `Re-Ingest` button currently clears and rebuilds the graph (Idempotent Upsert is also supported but full refresh is safer for prototype). For production, we would use file watchers (Watchdog) to trigger incremental upserts via the implemented `upsert_node` methods.

**3. Cycle Handling**
Dependencies can be cyclic. We use Neo4j's `shortestPath` which handles cycles naturally, and our custom `blast_radius` Cypher query uses distinct node collection (`MATCH (n)-[*]->(m)`) which avoids infinite loops by visiting nodes once.

**4. Query Mapping**
We use a "Tool Calling" approach. The LLM does **not** query the graph directly (to avoid hallucination and syntax errors). It outputs a JSON intent that maps to a specific Python function in `QueryEngine`.

**5. Failure Handling**
If the LLM can't determine intent, it asks for clarification. If the Graph returns empty, we show "No data found". The UI handles connection errors to Neo4j gracefully with status indicators.

**6. Scale Considerations (10K Nodes)**
Neo4j handles millions of nodes easily. The bottleneck would be the python `networkx` in-memory processing if we used it, but we delegated heavy lifting to Cypher. Visualization in the UI would need pagination for 10K nodes.

**7. Why Neo4j?**
Chosen for its native graph traversals (`[*..5]`), visual browser, and enforcing constraints. SQL recursive CTEs are painful for variable-depth "blast radius" queries.

## ⚖️ Tradeoffs & Limitations

1. **Security**: API Keys are passed via environment variables, but for production, we should use a dedicated Secrets Manager (Vault, AWS Secrets Manager). The UI has no authentication.
2. **Persistence**: We assume `docker-compose.yml` is the source of truth. Real-world systems drift. A production version would query the live Kubernetes API or AWS API directly rather than static files.
3. **Scale**: The current "Blast Radius" implementation fetches all downstream nodes. For a graph with millions of nodes, we would need to limit depth (e.g., `[*..5]`) and implement pagination.
4. **LLM Dependency**: The system relies on the LLM to route intent. If the LLM is down or hallucinating, the query fails. We mitigated this with strict schema enforcement but a fallback keyword search would be a good addition.

## 🛠️ Tech Stack
- **Language**: Python 3.11
- **Database**: Neo4j 5.15
- **UI**: Streamlit
- **LLM**: Groq (Llama 3.3 70B)

## 📂 Directory Structure
- `connectors/`: Parsing logic
- `graph/`: Database interaction
- `chat/`: LLM Logic
- `ui/`: Frontend
- `data/`: Sample configs

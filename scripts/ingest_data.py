from neo4j import GraphDatabase
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors.docker_compose import DockerComposeConnector
from connectors.teams import TeamsConnector
from connectors.kubernetes import KubernetesConnector
from graph.storage import GraphStorage

def ingest():
    print("Starting Ingestion...")
    storage = GraphStorage()
    
    # Optional: Clear graph to avoid stale data during dev
    print("Clearing existing graph...")
    storage.clear_graph()
    
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    
    connectors = [
        DockerComposeConnector(os.path.join(base_path, 'docker-compose.yml')),
        TeamsConnector(os.path.join(base_path, 'teams.yaml')),
        KubernetesConnector(os.path.join(base_path, 'k8s-deployments.yaml'))
    ]
    
    for c in connectors:
        print(f"Running {c.__class__.__name__}...")
        nodes, edges = c.load()
        
        print(f"  Upserting {len(nodes)} nodes...")
        for n in nodes:
            storage.upsert_node(n)
            
        print(f"  Upserting {len(edges)} edges...")
        for e in edges:
            storage.upsert_edge(e)
            
    storage.close()
    print("Ingestion Complete.")

if __name__ == "__main__":
    try:
        ingest()
    except Exception as e:
        print(f"Ingestion failed: {e}")
        # Don't exit with error if it's just connection issues during build, 
        # but for now we want to see it fail.
        sys.exit(1)

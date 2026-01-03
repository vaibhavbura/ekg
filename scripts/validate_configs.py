import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors.docker_compose import DockerComposeConnector
from connectors.teams import TeamsConnector
from connectors.kubernetes import KubernetesConnector

def main():
    print("Validating Connectors...")
    
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    
    connectors = [
        DockerComposeConnector(os.path.join(base_path, 'docker-compose.yml')),
        TeamsConnector(os.path.join(base_path, 'teams.yaml')),
        KubernetesConnector(os.path.join(base_path, 'k8s-deployments.yaml'))
    ]
    
    total_nodes = 0
    total_edges = 0
    
    all_nodes = []
    all_edges = []

    for c in connectors:
        print(f"Running {c.__class__.__name__}...")
        nodes, edges = c.load()
        print(f"  -> Found {len(nodes)} nodes and {len(edges)} edges.")
        total_nodes += len(nodes)
        total_edges += len(edges)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    print("-" * 30)
    print(f"Total Nodes: {total_nodes}")
    print(f"Total Edges: {total_edges}")
    
    # Print sample to verify
    if all_nodes:
        print(f"\nSample Node: {all_nodes[0]}")
    if all_edges:
        print(f"Sample Edge: {all_edges[0]}")

if __name__ == "__main__":
    main()

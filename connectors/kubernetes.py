import yaml
import os
from typing import List, Dict, Tuple
from .base import BaseConnector

class KubernetesConnector(BaseConnector):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> Tuple[List[Dict], List[Dict]]:
        if not os.path.exists(self.file_path):
            print(f"Warning: File {self.file_path} not found.")
            return [], []

        with open(self.file_path, 'r') as f:
            try:
                # multiple documents
                documents = list(yaml.safe_load_all(f))
            except yaml.YAMLError as exc:
                print(f"Error parsing YAML: {exc}")
                return [], []

        nodes = []
        edges = []

        for doc in documents:
            if not doc: 
                continue
            kind = doc.get('kind')
            metadata = doc.get('metadata', {})
            name = metadata.get('name')
            
            if kind == 'Deployment' and name:
                # This corresponds to a Service in our graph
                # node_id should match DockerComposeConnector: "service:name" (lowercase prefix)
                node_id = f"service:{name}"
                
                spec = doc.get('spec', {})
                template_spec = spec.get('template', {}).get('spec', {})
                containers = template_spec.get('containers', [])
                
                # Extract image and resources from first container
                image = ""
                resources = {}
                if containers:
                    c = containers[0]
                    image = c.get('image', '')
                    resources = c.get('resources', {})

                # We can create a node. 
                # If we use UPSERT logic in Neo4j, this will merge with existing nodes 
                # or create new ones if they didn't exist in docker-compose.
                node = {
                    "id": node_id,
                    "type": "Service",
                    "name": name,
                    "properties": {
                        "k8s_image": image,
                        "k8s_replicas": spec.get('replicas', 1),
                        "k8s_namespace": metadata.get('namespace', 'default'),
                        "k8s_resources": str(resources)
                    }
                }
                nodes.append(node)
                
                # We could infer env vars from K8s too, similar to Docker Compose
                # But let's stick to the bonus requirement: Metadata enrichment.
                
        return nodes, edges

import yaml
import os
from typing import List, Dict, Tuple
from .base import BaseConnector

class DockerComposeConnector(BaseConnector):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> Tuple[List[Dict], List[Dict]]:
        if not os.path.exists(self.file_path):
            print(f"Warning: File {self.file_path} not found.")
            return [], []

        with open(self.file_path, 'r') as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                print(f"Error parsing YAML: {exc}")
                return [], []

        nodes = []
        edges = []
        services = data.get('services', {})

        for service_name, config in services.items():
            # Determines Node Type
            labels = config.get('labels', {})
            # Default type is 'Service', but labels can override (e.g., type: Database)
            node_label = labels.get('type', 'service').capitalize()
            
            # Additional logic for common images if label is missing
            image = config.get('image', '')
            if 'postgres' in image and node_label == 'Service':
                node_label = 'Database'
            elif 'redis' in image and node_label == 'Service':
                node_label = 'Cache'

            # ID Convention: lowercase_type:name (e.g. service:payment-service)
            node_id = f"{node_label.lower()}:{service_name}"
            
            # Construct Node
            node = {
                "id": node_id,
                "type": node_label,
                "name": service_name,
                "properties": {
                    "image": image,
                    "build": config.get('build', ''),
                }
            }
            # Add labels to properties
            for k, v in labels.items():
                node['properties'][k] = v
            
            nodes.append(node)

        # Second pass for Edges to resolve Types
        # Create a map of service_name -> node_type
        service_type_map = {n['name']: n['type'] for n in nodes}

        for service_name, config in services.items():
            source_type = service_type_map.get(service_name)
            # Ensure we found the node (e.g. might be external or ignored)
            if not source_type:
                continue

            # ID Convention: lowercase_type:name
            # CRITICAL: Must match node creation logic which uses .lower()
            source_id = f"{source_type.lower()}:{service_name}"

            # 1. depends_on (Explicit dependency -> DEPENDS_ON)
            depends_on = config.get('depends_on', [])
            if isinstance(depends_on, list):
                for dep in depends_on:
                    target_type = service_type_map.get(dep)
                    if target_type:
                        target_id = f"{target_type.lower()}:{dep}"
                        edges.append({
                            "id": f"edge:{service_name}-depends_on-{dep}",
                            "type": "depends_on",
                            "source": source_id,
                            "target": target_id,
                            "properties": {}
                        })

            # 2. Parse Environment Variables for Semantic Edges
            env = config.get('environment', [])
            env_dict = {}
            if isinstance(env, list):
                for item in env:
                    if '=' in item:
                        k, v = item.split('=', 1)
                        env_dict[k] = v
            elif isinstance(env, dict):
                env_dict = env

            for k, v in env_dict.items():
                # Heuristic to find URL-like variables
                if not (k.endswith('_URL') or '://' in v):
                    continue
                
                target_service = None
                
                # Heuristic URL Parser
                # Examples: 
                # redis://redis-main:6379, postgresql://postgres:secret@users-db:5432/users
                # http://payment-service:8083
                
                parts = v.split('://')
                if len(parts) > 1:
                    remainder = parts[1]
                    # Remove user:pass@ if present
                    if '@' in remainder:
                        remainder = remainder.split('@')[1]
                    
                    # Extract host
                    host_part = remainder.split(':')[0]
                    host_part = host_part.split('/')[0]
                    
                    if host_part in service_type_map:
                        target_service = host_part
                
                if target_service:
                    target_type = service_type_map.get(target_service)
                    target_id = f"{target_type.lower()}:{target_service}"
                    
                    # Determine Edge Type based on Var Name
                    edge_type = "calls" # Default
                    if "DATABASE_URL" in k:
                        edge_type = "depends_on"
                    elif "REDIS_URL" in k:
                        edge_type = "uses"
                    elif "_SERVICE_URL" in k:
                        edge_type = "calls"

                    edges.append({
                        "id": f"edge:{service_name}-{edge_type}-{target_service}",
                        "type": edge_type,
                        "source": source_id,
                        "target": target_id,
                        "properties": {"env_var": k}
                    })
                        
        return nodes, edges

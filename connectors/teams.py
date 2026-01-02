import yaml
import os
from typing import List, Dict, Tuple
from .base import BaseConnector

class TeamsConnector(BaseConnector):
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
        teams = data.get('teams', [])

        for team in teams:
            team_name = team.get('name')
            if not team_name:
                continue

            # Create Team Node
            node_id = f"team:{team_name}" # ID stays lower case by convention if desired, but label below is Team
            node = {
                "id": node_id,
                "type": "Team",
                "name": team_name,
                "properties": {
                    "lead": team.get('lead'),
                    "slack": team.get('slack_channel'),
                    "pagerduty": team.get('pagerduty_schedule')
                }
            }
            nodes.append(node)

            # Create Ownership Edges
            owns = team.get('owns', [])
            for item in owns:
                # We don't know the type of the item (service or db) strictly from teams.yaml
                # But our ID convention is type:name.
                
                # Heuristic to match DockerComposeConnector's new Capitalized Types (but lowercase IDs)
                target_label = 'Service'
                if item.endswith('-db'):
                    target_label = 'Database'
                elif item == 'redis-main':
                    target_label = 'Cache'
                
                # ID Convention: lowercase_type:name
                target_id = f"{target_label.lower()}:{item}"
                
                # Direction: Service OWNED_BY Team
                edges.append({
                    "id": f"edge:{item}-owned_by-{team_name}",
                    "type": "OWNED_BY",
                    # REVERSED: Source is the Resource, Target is the Team
                    "source": target_id,
                    "target": node_id, 
                    "properties": {}
                })

        return nodes, edges

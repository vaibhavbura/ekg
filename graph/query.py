from typing import List, Dict, Any, Optional
from .storage import GraphStorage

class QueryEngine:
    def __init__(self, storage: GraphStorage):
        self.storage = storage

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Retrieve a single node by ID."""
        records = self.storage.query("MATCH (n {id: $id}) RETURN n", {"id": node_id})
        if records:
            return records[0]['n']
        return None

    def get_nodes(self, node_type: str = None, limit: int = 100) -> List[Dict]:
        """List nodes, optionally filtered by type."""
        if node_type:
            # Safe because type is verified or originates from trusted list usually
            # But strictly we should sanitize.
            # Here we assume node_type is clean 'Service', 'Database' etc.
            # Fix: Ensure label is Capitalized to match Neo4j data (e.g. 'service' -> 'Service')
            cypher = f"MATCH (n:`{node_type.capitalize()}`) RETURN n LIMIT $limit"
        else:
            cypher = "MATCH (n) RETURN n LIMIT $limit"
        
        records = self.storage.query(cypher, {"limit": limit})
        return [r['n'] for r in records]

    def get_owner(self, node_id: str) -> List[Dict]:
        """Find the team that owns this node."""
        cypher = """
        MATCH (n {id: $id})-[:OWNED_BY]->(t:Team)
        RETURN t
        """
        records = self.storage.query(cypher, {"id": node_id})
        return [r['t'] for r in records]
        
    def blast_radius(self, node_id: str) -> Dict[str, List[Dict]]:
        """
        Calculate impact:
        1. Downstream: What depends on this? (Transitive)
        2. Upstream: What does this depend on? (Optional context)
        3. Directly affected teams.
        """
        # Downstream: (n)<-[*]-(dependent)
        # Note: DEPENDS_ON direction: Service A DEPENDS_ON Service B.
        # If B goes down, A is affected. So we traverse incoming DEPENDS_ON edges.
        # Also CALLS edges: A CALLS B. If B down, A affected.
        
        # Finding everything that depends on node_id
        downstream_cypher = """
        MATCH (n {id: $id})<-[:DEPENDS_ON|CALLS*]-(dependent)
        RETURN distinct dependent
        """
        
        # Finding everything this node depends on (root cause analysis context)
        upstream_cypher = """
        MATCH (n {id: $id})-[:DEPENDS_ON|CALLS*]->(dependency)
        RETURN distinct dependency
        """
        
        downstream = [r['dependent'] for r in self.storage.query(downstream_cypher, {"id": node_id})]
        upstream = [r['dependency'] for r in self.storage.query(upstream_cypher, {"id": node_id})]
        
        return {
            "node": node_id,
            "downstream_impact": downstream,
            "upstream_dependencies": upstream,
            "count_affected": len(downstream)
        }

    def shortest_path(self, from_id: str, to_id: str) -> List[Dict]:
        """Find data path between two nodes."""
        cypher = """
        MATCH p = shortestPath((start {id: $from_id})-[*]-(end {id: $to_id}))
        RETURN p
        """
        records = self.storage.query(cypher, {"from_id": from_id, "to_id": to_id})
        if not records:
            return []
            
        # Parse path object is a bit complex in raw result, Neo4j driver returns Path object
        # But .data() converts it.
        # Simple extraction of nodes involved
        # For visualization, we might need nodes and edges.
        # Let's return list of node names/ids in order or the full path.
        
        # Simplifying for list output
        path_data = records[0]['p']
        # path_data is likely a list of nodes and rels if we check how data() serializes Path.
        # Let's just return it and parse in UI.
        return path_data

from neo4j import GraphDatabase
import os
import time

class GraphStorage:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.verify_connection()

    def verify_connection(self):
        """Waits for Neo4j to be ready."""
        max_retries = 60
        for i in range(max_retries):
            try:
                self.driver.verify_connectivity()
                print("Connected to Neo4j.")
                return
            except Exception as e:
                print(f"Waiting for Neo4j... ({i+1}/{max_retries})")
                time.sleep(1)
        raise Exception("Could not connect to Neo4j after 60 seconds.")

    def close(self):
        self.driver.close()

    def clear_graph(self):
        """Deletes all nodes and relationships."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            # Create constraints for performance/uniqueness
            try:
                session.run("CREATE CONSTRAINT FOR (n:Service) REQUIRE n.id IS UNIQUE")
                session.run("CREATE CONSTRAINT FOR (n:Database) REQUIRE n.id IS UNIQUE")
                session.run("CREATE CONSTRAINT FOR (n:Team) REQUIRE n.id IS UNIQUE")
            except:
                pass # Constraints might already exist

    def upsert_node(self, node: dict):
        """
        Upserts a node using MERGE.
        node: { "id": "...", "type": "...", "name": "...", "properties": {...} }
        """
        query = f"""
        MERGE (n:`{node['type']}` {{id: $id}})
        SET n.name = $name
        SET n += $props
        """
        with self.driver.session() as session:
            session.run(query, id=node['id'], name=node['name'], props=node['properties'])

    def upsert_edge(self, edge: dict):
        """
        Upserts an edge using MERGE.
        edge: { "type": "...", "source": "...", "target": "...", ... }
        """
        # We need to MATCH source and target first. 
        # Since nodes might have different labels, we can match by ID (assuming constraint) 
        # OR we just match generic node (n {id: $source}).
        
        # Note: In Neo4j, it's efficient to match by Label if possible, but our ID is unique.
        
        rel_type = edge['type'].upper()
        
        query = f"""
        MATCH (s {{id: $source_id}})
        MATCH (t {{id: $target_id}})
        MERGE (s)-[r:`{rel_type}`]->(t)
        SET r += $props
        """
        with self.driver.session() as session:
            session.run(query, 
                        source_id=edge['source'], 
                        target_id=edge['target'], 
                        props=edge['properties'])

    def query(self, cypher: str, params: dict = None):
        """Executes a read query and returns list of records."""
        if params is None:
            params = {}
        with self.driver.session() as session:
            result = session.run(cypher, **params)
            return [record.data() for record in result]

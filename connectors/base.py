from abc import ABC, abstractmethod
from typing import List, Dict, Tuple

class BaseConnector(ABC):
    """
    Abstract base class for all connectors.
    Connectors are responsible for parsing a specific source file
    and returning a list of nodes and edges in a standardized dictionary format.
    """

    @abstractmethod
    def load(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Parses the source and returns a tuple of (nodes, edges).
        
        Node format:
        {
            "id": "type:name",
            "type": "service|database|team|etc",
            "name": "friendly_name",
            "properties": { "key": "value" }
        }

        Edge format:
        {
            "id": "edge:source-type-target",
            "type": "calls|depends_on|owns",
            "source": "type:source_id",
            "target": "type:target_id",
            "properties": {}
        }
        """
        pass

import os
import json
from openai import OpenAI
from typing import Dict, Any

class ChatRouter:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            # Fallback or error
            print("Warning: GROQ_API_KEY not set.")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )

        self.system_prompt = """
You are an expert Engineering Knowledge Graph Assistant.
Your job is to translate user natural language queries into specific Graph Query Intent JSON.
You DO NOT answer the question. You only output the JSON to query the graph.

AVAILABLE INTENTS (Tools):
1. `get_owner(node_id)`: For "Who owns X?", "Team for X".
2. `blast_radius(node_id)`: For "What breaks if X goes down?", "Impact of X", "Dependencies of X".
3. `upstream(node_id)`: For "What depends on X?", "Root cause for X".
4. `shortest_path(from_id, to_id)`: For "How does A connect to B?", "Path between A and B".
5. `get_node(node_id)`: For "Details about X", "Show me X".
6. `get_nodes(type)`: For "List all services", "Show databases". `type` can be 'service', 'database', 'team'.
7. `pager(node_id)`: For "Who should I page?", "Is X down?", "X failed", "Oncall for X".

ENTITY RESOLUTION:
- Users might say "order service" -> You must map to ID "service:order-service" or "order-service" (fuzzy matches handled by backend if needed, but try to guess standard IDs).
- Teams start with `team:`.
- Services start with `service:`.
- Databases start with `database:`.
- Caches start with `cache:`.

OUTPUT FORMAT:
{
  "intent": "function_name",
  "parameters": {
    "arg_name": "value"
  },
  "explanation": "Brief reason for this query"
}

EXAMPLE:
User: "Who owns the payment service?"
Output:
{
  "intent": "get_owner",
  "parameters": { "node_id": "service:payment-service" },
  "explanation": "User is asking for ownership."
}

EXAMPLE:
User: "Who should I page if orders-db is down?"
Output:
{
  "intent": "pager",
  "parameters": { "node_id": "database:orders-db" },
  "explanation": "User is asking for on-call/paging info."
}
"""

    def route(self, user_query: str, history: list = None) -> Dict[str, Any]:
        if not self.client:
            return {"error": "No LLM Client configured."}

        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if history:
            # Add a few recent messages for context resolution (e.g. "What about THAT service?")
            # limit to last 2 turns
            # Sanitize history to strip 'data' or other UI-specific fields not supported by OpenAI API
            sanitized_history = []
            for msg in history[-4:]:
                clean_msg = {
                    "role": msg.get("role"),
                    "content": msg.get("content")
                }
                sanitized_history.append(clean_msg)
            
            messages.extend(sanitized_history)
        
        messages.append({"role": "user", "content": user_query})

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                response_format={ "type": "json_object" },
                temperature=0.0
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            return {"error": str(e)}

    def summarize_response(self, user_query: str, query_result: Any) -> str:
        """
        Optional: Convert structured graph data back to natural language.
        """
        if not self.client:
            return str(query_result)
            
        summary_prompt = f"""
        User asked: "{user_query}"
        Graph Database returned: {json.dumps(query_result, default=str)}
        
        Please provide a concise, friendly, engineer-to-engineer answer parsing the graph data.
        If the data is empty, say so politely.
        Do not hallucinate edges that aren't there.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error summarizing: {e}. Raw Data: {query_result}"

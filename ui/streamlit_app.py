import streamlit as st
import sys
import os
import json
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graph.storage import GraphStorage
from graph.query import QueryEngine
from chat.router import ChatRouter
from chat.context import ChatContext
from scripts.ingest_data import ingest

st.set_page_config(page_title="Engineering Knowledge Graph", page_icon="🕸️", layout="wide")

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "router" not in st.session_state:
    st.session_state.router = ChatRouter()

# Lazy Init for Graph to avoid connection issues on pure UI refresh if DB down
if "graph_ready" not in st.session_state:
    st.session_state.graph_ready = False

@st.cache_resource
def get_graph_components():
    """Cached resource for DB connection"""
    try:
        storage = GraphStorage()
        query_engine = QueryEngine(storage)
        return storage, query_engine
    except Exception as e:
        return None, None

def check_and_ingest(query_engine):
    """Check if graph has nodes, if not, ingest."""
    try:
        nodes = query_engine.get_nodes(limit=1)
        if not nodes:
            st.toast("Empty graph detected. Ingesting data...", icon="🔄")
            ingest() 
            st.toast("Ingestion Complete!", icon="✅")
    except Exception as e:
        st.error(f"Error checking graph state: {e}")

# Sidebar
with st.sidebar:
    st.title("🕸️ EKG Assistant")
    st.markdown("---")
    st.subheader("Capabilities")
    st.markdown("""
    - **Ownership**: "Who owns service X?"
    - **Dependencies**: "What does X depend on?"
    - **Blast Radius**: "What breaks if X fails?"
    - **Pathfinding**: "Path from A to B?"
    """)
    st.markdown("---")
    
    # Status Indicator
    storage, query_engine = get_graph_components()
    if storage:
        st.success("Actively connected to Neo4j")
        st.session_state.graph_ready = True
        if st.button("Re-Ingest Data"):
            with st.spinner("Ingesting..."):
                ingest()
                st.success("Done!")
    else:
        st.error("Neo4j Disconnected")
        st.info("Ensure `docker-compose up` is running.")

# Main Interface
st.title("Engineering Knowledge Graph")
st.caption("Ask questions about your infrastructure, teams, and dependencies.")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "data" in message:
             with st.expander("View Graph Data"):
                 st.json(message["data"])

# User Input
if prompt := st.chat_input("Ask a question..."):
    # 1. Add User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Process with LLM Router
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        if not st.session_state.graph_ready:
             message_placeholder.error("Graph Database is not available.")
        else:
            with st.spinner("Analyzing intent..."):
                router_response = st.session_state.router.route(
                    prompt, 
                    history=st.session_state.messages
                )
            
            intent = router_response.get("intent")
            params = router_response.get("parameters", {})
            explanation = router_response.get("explanation", "")
            
            # Show intent (debug/transparency)
            intent = router_response.get("intent")
            params = router_response.get("parameters", {})
            explanation = router_response.get("explanation", "")
            
            if "error" in router_response:
                st.error(f"Router Error: {router_response['error']}")
                st.caption(f"Raw Response: {router_response}")
            else:
                st.caption(f"Intent: `{intent}` | Params: `{params}`")
            
            # 3. Execute Graph Query
            result = None
            try:
                if intent == "get_owner":
                    result = query_engine.get_owner(params.get("node_id"))
                elif intent == "blast_radius":
                    result = query_engine.blast_radius(params.get("node_id"))
                elif intent == "upstream":
                    # Blast radius actually covers upstream/downstream context usually, 
                    # but let's just use get_nodes w/ pattern or mapped function
                    # We mapped upstream in router prompt to `upstream` intent often, 
                    # but query engine has blast_radius returning both.
                    # Or we can make a specific upstream method. 
                    # Let's map to blast_radius for now or custom logic.
                    # Actually I implemented `blast_radius` which returns upstream/downstream dict.
                    result = query_engine.blast_radius(params.get("node_id"))
                elif intent == "shortest_path":
                    result = query_engine.shortest_path(params.get("from_id"), params.get("to_id"))
                elif intent == "get_node":
                    result = query_engine.get_node(params.get("node_id"))
                elif intent == "get_nodes":
                    result = query_engine.get_nodes(params.get("type"))
                elif intent == "pager":
                    # Safety net: Ensure ID is lowercase to match graph conventions
                    node_id = params.get("node_id", "").lower()
                    
                    # Fetch Node for direct oncall (if any)
                    node_info = query_engine.get_node(node_id)
                    # Fetch Owner for team oncall
                    owners = query_engine.get_owner(node_id)
                    
                    if not node_info and not owners:
                        result = f"Could not find resource or owners for {node_id}."
                    else:
                        # Note: Neo4j .data() returns flattened properties, so we access them directly.
                        if owners:
                            owner_node = owners[0]
                            team_name = owner_node.get('name', 'Unknown Team')
                            team_pager = owner_node.get('pagerduty', 'N/A')
                            team_lead = owner_node.get('lead', 'N/A')
                        else:
                            team_name = "Unknown Team"
                            team_pager = "N/A"
                            team_lead = "N/A"
                        
                        # Service-level oncall override
                        service_oncall = "N/A"
                        if node_info:
                            service_oncall = node_info.get('oncall', 'N/A')
                        
                        # Fallback logic: Service oncall > Team Lead
                        primary_oncall = service_oncall if service_oncall != "N/A" else team_lead
                        
                        result = f"{node_id} is owned by the {team_name}. Primary on-call: {primary_oncall} (PagerDuty: {team_pager})."
                else:
                    result = "Unknown intent or generic query."

            except Exception as e:
                result = f"Error Querying Graph: {str(e)}"

            # 4. Summarize with LLM
            with st.spinner("Synthesizing answer..."):
                final_answer = st.session_state.router.summarize_response(prompt, result)
            
            message_placeholder.markdown(final_answer)
            
            # 5. Append to History
            st.session_state.messages.append({
                "role": "assistant", 
                "content": final_answer,
                "data": result # Store raw data for expander
            })
            
            # Optional: Show structured card for Blast Radius
            if intent == "blast_radius" and isinstance(result, dict):
                st.warning(f"Blast Radius Analysis for {result.get('node')}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Downstream (Breaks if this fails):**")
                    for item in result.get('downstream_impact', []):
                        st.code(item.get('id', 'Unknown'))
                with col2:
                    st.markdown("**UpstreamDependencies (Root causes):**")
                    for item in result.get('upstream_dependencies', []):
                        st.code(item.get('id', 'Unknown'))

# Initial check
if st.session_state.graph_ready:
    check_and_ingest(query_engine)

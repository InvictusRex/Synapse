"""
Synapse UI - Streamlit Interface for Multi-Agent System
"""
import streamlit as st
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Page config
st.set_page_config(
    page_title="Synapse - Multi-Agent System",
    page_icon="🧠",
    layout="wide"
)

# Check API key
if not os.environ.get("GROQ_API_KEY"):
    st.error("⚠️ GROQ_API_KEY not set!")
    st.code('$env:GROQ_API_KEY="your-key-here"', language="powershell")
    st.info("Get free key at: https://console.groq.com")
    st.stop()

# Initialize Synapse (cached)
@st.cache_resource
def init_synapse():
    from synapse import Synapse
    return Synapse()

try:
    synapse = init_synapse()
except Exception as e:
    st.error(f"Failed to initialize Synapse: {e}")
    st.stop()

# Header
st.title("🧠 Synapse")
st.caption("Multi-Agent System with A2A Communication & MCP Tools")

# Sidebar - System Status
with st.sidebar:
    st.header("📊 System Status")
    
    status = synapse.get_status()
    
    # Agents
    st.subheader("🤖 Agents")
    for agent in status["agents"]:
        icon = "🟢" if agent["running"] else "🔴"
        st.markdown(f"{icon} **{agent['name']}**")
        with st.expander(f"Tools: {len(agent['tools'])}"):
            for tool in agent["tools"]:
                st.text(f"  • {tool}")
    
    st.divider()
    
    # MCP Stats
    st.subheader("🔧 MCP Server")
    mcp = status["mcp"]
    st.metric("Tools Registered", mcp["tools_registered"])
    st.metric("Total Executions", mcp["total_executions"])
    
    st.divider()
    
    # A2A Bus
    st.subheader("📬 A2A Message Bus")
    bus = status["bus"]
    st.metric("Messages Sent", bus["message_count"])
    st.text(f"Agents: {', '.join(bus['registered_agents'])}")

# Main tabs
tab_execute, tab_messages, tab_architecture = st.tabs([
    "🚀 Execute", "📬 A2A Messages", "🏗️ Architecture"
])

# ==================== EXECUTE TAB ====================
with tab_execute:
    st.subheader("Enter your request")
    
    # Examples
    with st.expander("📝 Example requests"):
        examples = [
            "List files on my Desktop",
            "What time is it?",
            "Get system information",
            "Calculate 25 * 17 + sqrt(144)",
            "Write an article about artificial intelligence and save it to my Desktop as ai_article.txt",
            "Create a folder called Projects on my Desktop",
            "Fetch the webpage https://example.com and summarize it"
        ]
        cols = st.columns(2)
        for i, ex in enumerate(examples):
            with cols[i % 2]:
                if st.button(ex, key=f"ex_{i}", use_container_width=True):
                    st.session_state.user_input = ex
    
    # Input
    user_input = st.text_area(
        "What would you like to do?",
        value=st.session_state.get("user_input", ""),
        height=100,
        placeholder="Describe what you want to accomplish..."
    )
    
    if st.button("🚀 Execute", type="primary"):
        if user_input:
            # Process through multi-agent system
            with st.spinner("Processing through agents..."):
                result = synapse.process(user_input)
            
            # Show stages
            st.subheader("📋 Execution Stages")
            
            stages = result.get("stages", {})
            
            # Stage 1: Parsing
            with st.expander("1️⃣ Interaction Agent: Input Parsing", expanded=False):
                if "parsing" in stages:
                    parsed = stages["parsing"].get("parsed", {})
                    st.json(parsed)
            
            # Stage 2: Planning
            with st.expander("2️⃣ Planner Agent: Execution Plan", expanded=True):
                if "planning" in stages:
                    plan = stages["planning"].get("plan", {})
                    
                    if "description" in plan:
                        st.info(f"**Plan:** {plan.get('description')}")
                    
                    tasks = plan.get("tasks", [])
                    for task in tasks:
                        col1, col2, col3 = st.columns([1, 2, 3])
                        with col1:
                            st.code(task.get("task_id", "?"))
                        with col2:
                            st.markdown(f"**{task.get('agent', '?')}** → `{task.get('tool', '?')}`")
                        with col3:
                            deps = task.get("depends_on", [])
                            if deps:
                                st.caption(f"Depends on: {', '.join(deps)}")
                            st.json(task.get("args", {}))
            
            # Stage 3: Execution
            with st.expander("3️⃣ Orchestrator: Task Execution", expanded=True):
                if "execution" in stages:
                    exec_result = stages["execution"]
                    
                    # Task status
                    task_states = exec_result.get("task_states", {})
                    for task_id, state in task_states.items():
                        if state["status"] == "completed":
                            st.success(f"✅ {task_id}: Completed")
                        elif state["status"] == "failed":
                            st.error(f"❌ {task_id}: {state.get('error', 'Failed')}")
                        else:
                            st.warning(f"⏳ {task_id}: {state['status']}")
                    
                    st.metric("Tasks Completed", 
                             f"{exec_result.get('tasks_completed', 0)}/{exec_result.get('tasks_total', 0)}")
            
            # Final Result
            st.subheader("📄 Result")
            
            if result.get("success"):
                st.success("✅ Request completed successfully")
                
                # Show formatted result
                if result.get("formatted_result"):
                    st.markdown(result["formatted_result"])
                
                # Show outputs
                final = result.get("final_output", {})
                if final.get("all_outputs"):
                    with st.expander("📦 All Outputs"):
                        for output in final["all_outputs"]:
                            st.markdown(f"**{output.get('task')}** ({output.get('type')})")
                            content = output.get("content", "")
                            if len(str(content)) > 500:
                                st.text_area("Content", str(content), height=200, key=f"out_{output.get('task')}")
                            else:
                                st.code(str(content))
            else:
                st.error(f"❌ {result.get('error', 'Request failed')}")
            
            # Raw result
            with st.expander("🔍 Raw Result"):
                st.json(result)

# ==================== MESSAGES TAB ====================
with tab_messages:
    st.subheader("📬 A2A Message History")
    
    messages = synapse.get_message_history(100)
    
    if messages:
        for msg in reversed(messages):
            col1, col2 = st.columns([1, 4])
            with col1:
                st.caption(msg.get("timestamp", "")[:19])
            with col2:
                sender = msg.get("sender", "?")
                recipient = msg.get("recipient", "?")
                msg_type = msg.get("type", "?")
                
                if recipient == "broadcast":
                    st.markdown(f"**{sender}** 📢 *broadcast* `{msg_type}`")
                else:
                    st.markdown(f"**{sender}** → **{recipient}** `{msg_type}`")
                
                with st.expander("Payload"):
                    st.json(msg.get("payload", {}))
    else:
        st.info("No messages yet. Execute a request to see agent communication.")

# ==================== ARCHITECTURE TAB ====================
with tab_architecture:
    st.subheader("🏗️ System Architecture")
    
    st.markdown("""
    ```
    ┌─────────────────────────────────────────────────────────────────┐
    │                         USER INPUT                               │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    INTERACTION AGENT                             │
    │         Parses input, structures requests, formats results       │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                      PLANNER AGENT                               │
    │        Creates execution DAG, assigns tasks to agents            │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                   ORCHESTRATOR AGENT                             │
    │      Dispatches tasks, manages dependencies, aggregates results  │
    └─────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
    │   FILE AGENT    │   │  CONTENT AGENT  │   │   WEB AGENT     │
    │                 │   │                 │   │                 │
    │ • read_file     │   │ • generate_text │   │ • fetch_webpage │
    │ • write_file    │   │ • summarize     │   │ • download_file │
    │ • list_dir      │   │                 │   │                 │
    │ • copy/move     │   │                 │   │                 │
    └────────┬────────┘   └────────┬────────┘   └────────┬────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                      A2A MESSAGE BUS                             │
    │              Central communication for all agents                │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                       MCP SERVER                                 │
    │          Tool registry, validation, and execution                │
    └─────────────────────────────────────────────────────────────────┘
    ```
    """)
    
    st.divider()
    
    st.subheader("🤖 Agents")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Interaction Agent**
        - Parses natural language input
        - Extracts intent and entities
        - Formats results for user
        
        **Planner Agent**
        - Decomposes requests into tasks
        - Creates execution DAG
        - Assigns tasks to agents
        
        **Orchestrator Agent**
        - Executes plans
        - Manages dependencies
        - Passes data between tasks
        """)
    
    with col2:
        st.markdown("""
        **File Agent**
        - File read/write operations
        - Directory management
        - File search
        
        **Content Agent**
        - Text generation (AI)
        - Summarization
        - Content transformation
        
        **Web Agent**
        - Fetch web pages
        - Download files
        - Extract content
        
        **System Agent**
        - Shell commands
        - System info
        - Calculations
        """)
    
    st.divider()
    
    st.subheader("🔄 Communication Flow")
    st.markdown("""
    1. **User** sends request
    2. **Interaction Agent** parses and structures the request
    3. **Planner Agent** creates execution plan (DAG)
    4. **Orchestrator Agent** receives plan and dispatches tasks
    5. **Worker Agents** (File, Content, Web, System) execute tasks via A2A messages
    6. Results flow back through **Orchestrator** to **Interaction Agent**
    7. **User** receives formatted result
    
    All communication happens via the **A2A Message Bus** - agents don't call each other directly.
    All tool execution happens via the **MCP Server** - standardized interface.
    """)

# Footer
st.divider()
st.caption(f"Synapse Multi-Agent System | 7 Agents | {len(synapse.mcp.tools)} Tools | A2A + MCP")

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
            
            # ============ RESULTS FIRST (PROMINENT) ============
            st.subheader("📄 Result")
            
            exec_result = result.get("stages", {}).get("execution", {})
            tasks_completed = exec_result.get("tasks_completed", 0)
            tasks_failed = exec_result.get("tasks_failed", 0)
            tasks_total = exec_result.get("tasks_total", 0)
            
            if result.get("success"):
                if tasks_failed == 0:
                    st.success(f"✅ All {tasks_total} tasks completed successfully!")
                else:
                    st.warning(f"⚠️ Completed with issues: {tasks_completed}/{tasks_total} tasks succeeded")
            else:
                st.error(f"❌ Failed: {tasks_failed}/{tasks_total} tasks failed")
            
            # ============ SHOW ALL OUTPUTS PROMINENTLY ============
            final = result.get("final_output", {})
            all_outputs = final.get("all_outputs", [])
            
            # Also check task_results directly for better output
            task_results = exec_result.get("final_result", {}).get("last_task_result", {})
            
            # Display results based on content type
            for output in all_outputs:
                task_name = output.get("task", "")
                task_type = output.get("type", "")
                content = output.get("content", "")
                
                if task_type == "list_directory" and isinstance(content, dict):
                    # File listing
                    items = content.get("items", [])
                    directory = content.get("directory", "")
                    st.markdown(f"**📁 Contents of `{directory}`** ({len(items)} items)")
                    
                    # Create a nice table
                    if items:
                        cols = st.columns([3, 1, 2])
                        cols[0].markdown("**Name**")
                        cols[1].markdown("**Type**")
                        cols[2].markdown("**Size**")
                        
                        for item in items[:50]:  # Limit to 50 items
                            cols = st.columns([3, 1, 2])
                            icon = "📁" if item.get("type") == "folder" else "📄"
                            cols[0].text(f"{icon} {item.get('name', '')}")
                            cols[1].text(item.get("type", ""))
                            cols[2].text(item.get("size", "-"))
                        
                        if len(items) > 50:
                            st.caption(f"... and {len(items) - 50} more items")
                
                elif task_type == "get_system_info":
                    # System info
                    st.markdown("**💻 System Information**")
                    if isinstance(content, dict):
                        for key, value in content.items():
                            if key != "success":
                                st.text(f"  {key}: {value}")
                    else:
                        st.code(str(content))
                
                elif task_type == "get_datetime":
                    # Date/time
                    if isinstance(content, dict):
                        st.markdown(f"**🕐 Current Time:** {content.get('datetime', content)}")
                    else:
                        st.markdown(f"**🕐 Current Time:** {content}")
                
                elif task_type == "calculate":
                    # Calculation
                    if isinstance(content, dict):
                        expr = content.get("expression", "")
                        res = content.get("result", content)
                        st.markdown(f"**🔢 Calculation:** `{expr}` = **{res}**")
                    else:
                        st.markdown(f"**🔢 Result:** {content}")
                
                elif task_type == "generate_text":
                    # Generated content
                    st.markdown("**📝 Generated Content:**")
                    st.markdown(str(content))
                
                elif task_type == "write_file":
                    # File written
                    if isinstance(content, dict):
                        filepath = content.get("filepath", "")
                        st.markdown(f"**✅ File saved:** `{filepath}`")
                    else:
                        st.markdown(f"**✅ File saved:** {content}")
                
                elif task_type == "read_file":
                    # File content
                    st.markdown("**📄 File Content:**")
                    st.code(str(content)[:5000])
                
                elif task_type == "fetch_webpage":
                    # Webpage content
                    if isinstance(content, dict):
                        title = content.get("title", "")
                        text = content.get("content", "")
                        st.markdown(f"**🌐 Webpage: {title}**")
                        with st.expander("Page content"):
                            st.text(text[:3000])
                    else:
                        st.text(str(content)[:2000])
                
                elif task_type in ["create_folder", "move_file", "copy_file", "delete_file"]:
                    # File operations
                    st.markdown(f"**✅ {task_type.replace('_', ' ').title()}:** Completed")
                    if isinstance(content, dict):
                        for key, value in content.items():
                            if key not in ["success"] and value:
                                st.text(f"  {key}: {value}")
                
                else:
                    # Generic output
                    if content:
                        if isinstance(content, dict):
                            st.json(content)
                        elif len(str(content)) > 500:
                            st.text_area(f"Output from {task_type}", str(content), height=200)
                        else:
                            st.markdown(f"**Output:** {content}")
            
            # If no formatted outputs, show the last result
            if not all_outputs and task_results:
                st.markdown("**Result:**")
                if isinstance(task_results, dict):
                    # Filter out meta fields
                    display_result = {k: v for k, v in task_results.items() 
                                     if k not in ["success", "tool"]}
                    st.json(display_result)
                else:
                    st.code(str(task_results))
            
            # ============ EXECUTION DETAILS (COLLAPSED) ============
            with st.expander("🔍 Execution Details", expanded=False):
                stages = result.get("stages", {})
                
                # Parsing
                st.markdown("**1️⃣ Input Parsing**")
                if "parsing" in stages:
                    parsed = stages["parsing"].get("parsed", {})
                    st.caption(f"Intent: {parsed.get('intent', 'N/A')}")
                    st.caption(f"Task type: {parsed.get('task_type', 'N/A')}")
                
                # Planning
                st.markdown("**2️⃣ Execution Plan**")
                if "planning" in stages:
                    plan = stages["planning"].get("plan", {})
                    tasks = plan.get("tasks", [])
                    for task in tasks:
                        deps = task.get("depends_on", [])
                        dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
                        st.caption(f"• {task.get('task_id')}: {task.get('agent')} → {task.get('tool')}{dep_str}")
                
                # Task status
                st.markdown("**3️⃣ Task Execution**")
                task_states = exec_result.get("task_states", {})
                for task_id, state in task_states.items():
                    if state["status"] == "completed":
                        st.caption(f"✅ {task_id}: Completed")
                    else:
                        st.caption(f"❌ {task_id}: {state.get('error', 'Failed')}")
            
            # Raw result (fully collapsed)
            with st.expander("📋 Raw Result", expanded=False):
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

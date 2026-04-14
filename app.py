"""
Synapse - Multi-Agent System Demo
Streamlit UI for demonstrating MCP + A2A architecture
"""
import streamlit as st
import time
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.context import Context, ContextManager
from core.planner import PlannerAgent
from core.orchestrator import Orchestrator
from core.a2a_bus import get_bus
from mcp.tools import register_all_tools
from mcp.registry import get_registry

# Page config
st.set_page_config(
    page_title="Synapse - Multi-Agent System",
    page_icon="🧠",
    layout="wide"
)

# Initialize components
@st.cache_resource
def init_system():
    """Initialize the agent system"""
    register_all_tools()
    return {
        "context_manager": ContextManager(),
        "planner": PlannerAgent(),
        "orchestrator": Orchestrator(),
        "bus": get_bus()
    }

# Check for API key
if not os.environ.get("GROQ_API_KEY"):
    st.error("⚠️ GROQ_API_KEY not set. Please set it in your environment.")
    st.code("export GROQ_API_KEY='your-key-here'")
    st.info("Get a free API key at: https://console.groq.com")
    st.stop()

system = init_system()

# Header
st.title("🧠 Synapse")
st.markdown("**Multi-Agent System with MCP + A2A Architecture**")

# Sidebar - System Info
with st.sidebar:
    st.header("📊 System Status")
    
    # Show registered tools
    st.subheader("🔧 MCP Tools")
    registry = get_registry()
    for tool in registry.list_tools():
        with st.expander(f"**{tool['name']}**"):
            st.write(tool['description'])
            st.json(tool['parameters'])
    
    st.divider()
    
    # Show A2A agents
    st.subheader("🤖 A2A Agents")
    bus = get_bus()
    for agent_id in bus.queues.keys():
        st.success(f"✓ {agent_id}")
    
    st.divider()
    
    # Example queries
    st.subheader("💡 Try These")
    examples = [
        "Research AI in healthcare and write a summary",
        "Search for climate change news and create bullet points",
        "Generate a report on renewable energy",
        "Find information about machine learning trends and summarize"
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state.user_input = ex
            st.rerun()

# Main input
st.subheader("Enter your request")

# Initialize session state
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "execution_history" not in st.session_state:
    st.session_state.execution_history = []

user_input = st.text_area(
    "What would you like the agents to do?",
    value=st.session_state.user_input,
    height=100,
    placeholder="Example: Research AI trends and write a report"
)

col1, col2 = st.columns([1, 5])
with col1:
    execute_btn = st.button("🚀 Execute", type="primary", use_container_width=True)
with col2:
    clear_btn = st.button("🗑️ Clear", use_container_width=True)

if clear_btn:
    st.session_state.user_input = ""
    st.session_state.execution_history = []
    st.rerun()

# Execute workflow
if execute_btn and user_input:
    st.divider()
    
    # Create columns for visualization
    col_plan, col_exec = st.columns([1, 1])
    
    with col_plan:
        st.subheader("📋 Task Planning")
        
        with st.spinner("🤔 Analyzing request and planning tasks..."):
            # Create context
            context = system["context_manager"].create_context(user_input)
            st.info(f"Session: `{context.session_id}`")
            
            # Plan tasks
            try:
                task_nodes = system["planner"].plan(context)
                context.task_graph = task_nodes
                
                st.success(f"✅ Generated {len(task_nodes)} tasks")
                
                # Display task graph
                st.markdown("**Task Graph (DAG):**")
                for task in task_nodes:
                    deps_str = f" → depends on: {task.deps}" if task.deps else " (no dependencies)"
                    st.code(f"{task.id}: {task.tool}({list(task.args.keys())}){deps_str}")
                
            except Exception as e:
                st.error(f"Planning failed: {e}")
                st.stop()
    
    with col_exec:
        st.subheader("⚡ Execution")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_container = st.container()
        
        # Task status placeholders
        task_statuses = {}
        for task in context.task_graph:
            task_statuses[task.id] = status_container.empty()
            task_statuses[task.id].info(f"⏳ {task.id}: {task.tool} - Pending")
        
        # Execute with visual feedback
        def update_callback(task, status):
            if status == "running":
                task_statuses[task.id].warning(f"🔄 {task.id}: {task.tool} - Running...")
            elif status == "success":
                task_statuses[task.id].success(f"✅ {task.id}: {task.tool} - Complete")
            else:
                task_statuses[task.id].error(f"❌ {task.id}: {task.tool} - Failed")
            
            # Update progress
            done = len([t for t in context.task_graph if t.status in ["success", "failed"]])
            progress_bar.progress(done / len(context.task_graph))
        
        system["orchestrator"].on_task_update = update_callback
        
        # Execute
        with st.spinner("Executing task graph..."):
            success = system["orchestrator"].execute(context)
        
        if success:
            st.balloons()
            st.success("🎉 All tasks completed successfully!")
        else:
            st.warning("⚠️ Some tasks failed")
    
    # Results section
    st.divider()
    st.subheader("📄 Results")
    
    # Find the final result (usually the last successful task)
    final_result = None
    for task in reversed(context.task_graph):
        if task.status == "success" and task.result:
            final_result = task.result
            break
    
    if final_result:
        # Display based on result type
        if isinstance(final_result, dict):
            if "filepath" in final_result:
                st.success(f"📁 File saved: `{final_result['filepath']}`")
                # Try to read and display
                try:
                    with open(final_result['filepath'], 'r') as f:
                        st.text_area("File contents:", f.read(), height=300)
                except:
                    pass
            elif "results" in final_result:
                st.json(final_result)
            else:
                st.write(final_result)
        else:
            st.markdown(str(final_result))
    
    # Show all results in expander
    with st.expander("🔍 All Task Results"):
        for task in context.task_graph:
            st.markdown(f"**{task.id}: {task.tool}**")
            st.write(f"Status: {task.status}")
            if task.result:
                if isinstance(task.result, str) and len(task.result) > 500:
                    st.text_area(f"Result ({task.id})", task.result, height=150)
                else:
                    st.write(task.result)
            if task.error:
                st.error(task.error)
            st.divider()
    
    # A2A Message Log
    with st.expander("📨 A2A Message Bus Log"):
        messages = bus.get_message_history()
        for msg in messages[-20:]:  # Last 20 messages
            st.code(f"{msg['from']} → {msg['to']}: {msg['type']}")
    
    # Execution Log
    with st.expander("📝 Execution Log"):
        for event in context.execution_log:
            st.text(f"[{event['timestamp']}] {event['type']}: {event['task_id']} - {event['details'][:100]}")

# Footer
st.divider()
st.caption("Built with ❤️ for Philips Internship | MCP + A2A Architecture Demo")

"""
Synapse - Multi-Agent System Demo
Full-featured Streamlit UI with file upload, tool browser, and execution visualization
"""
import streamlit as st
import time
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.context import Context, ContextManager
from core.planner import PlannerAgent
from core.orchestrator import Orchestrator
from core.a2a_bus import get_bus
from mcp.tool_loader import register_all_tools
from mcp.registry import get_registry

# Page config
st.set_page_config(
    page_title="Synapse - Multi-Agent System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .tool-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
    .success-box {
        background-color: #d4edda;
        border-radius: 5px;
        padding: 10px;
    }
    .error-box {
        background-color: #f8d7da;
        border-radius: 5px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

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
api_configured = os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_configured:
    st.error("⚠️ No API key configured")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Option 1: Groq (Recommended)")
        st.code("$env:GROQ_API_KEY='your-key-here'", language="powershell")
        st.info("Get free key: https://console.groq.com")
    
    with col2:
        st.markdown("### Option 2: Gemini")
        st.code("$env:GEMINI_API_KEY='your-key-here'", language="powershell")
        st.info("Get free key: https://aistudio.google.com/apikey")
    
    st.stop()

system = init_system()
registry = get_registry()
bus = get_bus()

# Header
st.title("🧠 Synapse")
st.markdown("**Multi-Agent System with MCP + A2A Architecture**")

# Show active provider
provider = "Gemini" if os.environ.get("GEMINI_API_KEY") else "Groq"
st.success(f"✅ Connected to {provider} LLM")

# Create tabs
tab_main, tab_tools, tab_files, tab_settings = st.tabs(["🚀 Execute", "🔧 Tools", "📁 Files", "⚙️ Settings"])

# ==================== MAIN EXECUTION TAB ====================
with tab_main:
    # Sidebar for this tab
    with st.sidebar:
        st.header("💡 Example Queries")
        
        examples = {
            "🔍 Research": [
                "Search for latest AI news and summarize it",
                "Research climate change and create a report",
            ],
            "📄 Documents": [
                "Read the file at C:/path/to/file.txt and summarize it",
                "Create a report on renewable energy and save it to my Desktop",
            ],
            "🖼️ Images": [
                "Generate an image of a futuristic city at sunset",
                "Create an image of a robot playing chess",
            ],
            "📊 Data": [
                "Read the CSV at ~/data.csv and tell me what's in it",
                "Create a database and add some sample data",
            ],
            "🌐 Web": [
                "Fetch the webpage https://example.com and summarize it",
                "Download the file at URL and save it locally",
            ],
            "💻 System": [
                "List all files in my Documents folder",
                "What is 25 * 48 + sqrt(144)?",
                "Get current system information",
            ]
        }
        
        for category, queries in examples.items():
            with st.expander(category):
                for q in queries:
                    if st.button(q, key=q, use_container_width=True):
                        st.session_state.user_input = q
                        st.rerun()
        
        st.divider()
        st.caption(f"📊 {len(registry.tools)} tools available")
    
    # Main input
    st.subheader("What would you like the agents to do?")
    
    # Initialize session state
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    if "uploaded_file_path" not in st.session_state:
        st.session_state.uploaded_file_path = None
    
    # File upload
    uploaded_file = st.file_uploader(
        "📎 Upload a file (optional)",
        type=["txt", "pdf", "csv", "json", "xlsx", "docx", "png", "jpg"],
        help="Upload a file to process with your query"
    )
    
    if uploaded_file:
        # Save uploaded file temporarily
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, uploaded_file.name)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.session_state.uploaded_file_path = os.path.abspath(file_path)
        st.success(f"📁 File saved: `{st.session_state.uploaded_file_path}`")
        st.info("You can reference this file in your query!")
    
    # Text input
    user_input = st.text_area(
        "Enter your request",
        value=st.session_state.user_input,
        height=100,
        placeholder="Example: Search for AI trends and write a summary report",
        label_visibility="collapsed"
    )
    
    # If file was uploaded, suggest including it
    if st.session_state.uploaded_file_path and st.session_state.uploaded_file_path not in user_input:
        st.caption(f"💡 Tip: Reference your uploaded file with: `{st.session_state.uploaded_file_path}`")
    
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        execute_btn = st.button("🚀 Execute", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_btn:
        st.session_state.user_input = ""
        st.session_state.uploaded_file_path = None
        st.rerun()
    
    # Execute workflow
    if execute_btn and user_input:
        st.divider()
        
        # Create columns for visualization
        col_plan, col_exec = st.columns([1, 1])
        
        with col_plan:
            st.subheader("📋 Task Planning")
            
            with st.spinner("🤔 Analyzing request and planning tasks..."):
                context = system["context_manager"].create_context(user_input)
                st.info(f"Session: `{context.session_id}`")
                
                try:
                    task_nodes = system["planner"].plan(context)
                    context.task_graph = task_nodes
                    
                    st.success(f"✅ Generated {len(task_nodes)} tasks")
                    
                    # Display task graph
                    st.markdown("**Task Graph (DAG):**")
                    for task in task_nodes:
                        deps_str = f" → depends on: {task.deps}" if task.deps else ""
                        with st.expander(f"**{task.id}**: {task.tool}{deps_str}"):
                            st.json(task.args)
                    
                except Exception as e:
                    st.error(f"Planning failed: {e}")
                    st.stop()
        
        with col_exec:
            st.subheader("⚡ Execution")
            
            progress_bar = st.progress(0)
            status_container = st.container()
            
            task_statuses = {}
            for task in context.task_graph:
                task_statuses[task.id] = status_container.empty()
                task_statuses[task.id].info(f"⏳ {task.id}: {task.tool} - Pending")
            
            def update_callback(task, status):
                if status == "running":
                    task_statuses[task.id].warning(f"🔄 {task.id}: {task.tool} - Running...")
                elif status == "success":
                    task_statuses[task.id].success(f"✅ {task.id}: {task.tool} - Complete")
                else:
                    task_statuses[task.id].error(f"❌ {task.id}: {task.tool} - Failed")
                
                done = len([t for t in context.task_graph if t.status in ["success", "failed"]])
                progress_bar.progress(done / len(context.task_graph))
            
            system["orchestrator"].on_task_update = update_callback
            
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
        
        final_result = None
        for task in reversed(context.task_graph):
            if task.status == "success" and task.result:
                final_result = task.result
                break
        
        if final_result:
            if isinstance(final_result, dict):
                if "filepath" in final_result:
                    st.success(f"📁 File saved: `{final_result['filepath']}`")
                    try:
                        with open(final_result['filepath'], 'r') as f:
                            content = f.read()
                        st.text_area("File contents:", content, height=300)
                    except:
                        pass
                elif "content" in final_result:
                    st.markdown(final_result["content"])
                else:
                    st.json(final_result)
            else:
                st.markdown(str(final_result))
        
        # Expandable sections for details
        with st.expander("🔍 All Task Results"):
            for task in context.task_graph:
                st.markdown(f"**{task.id}: {task.tool}** - {task.status}")
                if task.result:
                    if isinstance(task.result, str) and len(task.result) > 500:
                        st.text_area(f"Result", task.result, height=150, key=f"result_{task.id}")
                    else:
                        st.write(task.result)
                if task.error:
                    st.error(task.error)
                st.divider()
        
        with st.expander("📨 A2A Message Log"):
            messages = bus.get_message_history()
            for msg in messages[-20:]:
                st.code(f"{msg['from']} → {msg['to']}: {msg['type']}")

# ==================== TOOLS TAB ====================
with tab_tools:
    st.subheader("🔧 Available MCP Tools")
    st.caption(f"Total: {len(registry.tools)} tools registered")
    
    # Group tools by category
    tool_categories = {
        "🤖 AI & Search": ["web_search", "generate_text", "summarize_text", "generate_report"],
        "📁 Filesystem": ["read_file", "write_file", "create_folder", "list_directory", "delete_file", 
                         "delete_folder", "move_file", "copy_file", "get_file_info", "search_files"],
        "📄 Documents": ["read_pdf", "get_pdf_info", "extract_pdf_tables", "read_word", "write_word"],
        "📊 Data": ["read_csv", "write_csv", "read_excel", "write_excel", "read_json", "write_json"],
        "🖼️ Images": ["generate_image", "resize_image", "convert_image", "get_image_info"],
        "🌐 HTTP/API": ["http_get", "http_post", "fetch_webpage", "download_file"],
        "🗄️ Database": ["create_database", "execute_sql", "create_table", "query_table", "list_tables"],
        "📧 Email": ["send_email", "check_email_config"],
        "💻 System": ["execute_python", "run_shell_command", "calculate", "get_system_info", "get_current_datetime"],
    }
    
    for category, tool_names in tool_categories.items():
        with st.expander(f"{category} ({len(tool_names)} tools)"):
            for tool_name in tool_names:
                tool = registry.get_tool(tool_name)
                if tool:
                    st.markdown(f"**`{tool.name}`**")
                    st.caption(tool.description)
                    with st.popover("View Schema"):
                        st.json(tool.parameters)
                    st.divider()

# ==================== FILES TAB ====================
with tab_files:
    st.subheader("📁 File Browser")
    
    # Directory input
    browse_dir = st.text_input(
        "Directory to browse",
        value=os.path.expanduser("~"),
        help="Enter a directory path to browse"
    )
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("📂 Browse", use_container_width=True):
            from mcp.tools.filesystem import list_directory
            result = list_directory(browse_dir)
            
            if result["success"]:
                st.session_state.browse_result = result
            else:
                st.error(result["error"])
    
    if "browse_result" in st.session_state and st.session_state.browse_result:
        result = st.session_state.browse_result
        st.success(f"📍 {result['directory']}")
        st.caption(f"{result['total_items']} items")
        
        # Display items
        for item in result["items"]:
            icon = "📁" if item["type"] == "folder" else "📄"
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.text(f"{icon} {item['name']}")
            with col2:
                st.caption(item.get('size_bytes', 0))
            with col3:
                st.caption(item['modified'][:10])

# ==================== SETTINGS TAB ====================
with tab_settings:
    st.subheader("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔑 API Keys")
        st.markdown(f"**LLM Provider:** {provider}")
        st.markdown(f"**GROQ_API_KEY:** {'✅ Set' if os.environ.get('GROQ_API_KEY') else '❌ Not set'}")
        st.markdown(f"**GEMINI_API_KEY:** {'✅ Set' if os.environ.get('GEMINI_API_KEY') else '❌ Not set'}")
        
        st.divider()
        
        st.markdown("### 📧 Email Configuration")
        from mcp.tools.email_tools import check_email_config
        email_config = check_email_config()
        st.json(email_config)
    
    with col2:
        st.markdown("### 💻 System Info")
        from mcp.tools.code_tools import get_system_info
        sys_info = get_system_info()
        st.json(sys_info)
        
        st.divider()
        
        st.markdown("### 📊 Session Stats")
        st.metric("Registered Tools", len(registry.tools))
        st.metric("A2A Messages", len(bus.get_message_history()))

# Footer
st.divider()
st.caption("Built with ❤️ for Philips Internship | MCP + A2A Architecture Demo | Synapse v2.0")

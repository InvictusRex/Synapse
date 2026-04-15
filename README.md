# Synapse - Multi-Agent AI System

A sophisticated multi-agent AI system with parallel DAG execution, multi-LLM support, persistent memory, and external API integration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              SYNAPSE                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐ │
│  │ Interaction │───▶│   Planner   │───▶│       Orchestrator          │ │
│  │   Agent     │    │   Agent     │    │    (Parallel DAG Exec)      │ │
│  └─────────────┘    └─────────────┘    └──────────────┬──────────────┘ │
│         │                  │                          │                 │
│         │                  │           ┌──────────────┼──────────────┐  │
│         │                  │           │              │              │  │
│         ▼                  ▼           ▼              ▼              ▼  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     WORKER AGENTS (Parallel)                     │   │
│  ├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤   │
│  │    File     │   Content   │     Web     │   System    │  Memory │   │
│  │   Agent     │   Agent     │    Agent    │   Agent     │  Agent  │   │
│  └─────────────┴─────────────┴─────────────┴─────────────┴─────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────┼───────────────────────────────┐   │
│  │                                 ▼                               │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │   │
│  │  │   LLM Pool    │  │   MCP Server  │  │    A2A Bus        │   │   │
│  │  │ Groq + Gemini │  │  Tool Registry │  │  Message Passing  │   │   │
│  │  │  (Fallback)   │  │               │  │                   │   │   │
│  │  └───────────────┘  └───────────────┘  └───────────────────┘   │   │
│  │                           CORE SERVICES                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │   │
│  │  │  Persistent   │  │    Vector     │  │    A2A HTTP       │   │   │
│  │  │    Memory     │  │    Memory     │  │     Server        │   │   │
│  │  │  (JSON File)  │  │  (Semantic)   │  │   (REST API)      │   │   │
│  │  └───────────────┘  └───────────────┘  └───────────────────┘   │   │
│  │                       PERSISTENCE & EXTERNAL                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Features

### 🔀 Parallel DAG Execution
- Tasks are organized as a Directed Acyclic Graph (DAG)
- Independent tasks execute in parallel across multiple workers
- Automatic dependency resolution and result propagation
- Configurable worker pool size (default: 4 workers)

### 🤖 Multi-LLM Support with Fallback
- **Primary**: Groq (llama-3.1-8b-instant) - Fast inference
- **Fallback**: Google Gemini (gemini-2.0-flash) - High quality
- Automatic failover when primary LLM is unavailable
- Load balancing across providers for parallel tasks
- Health monitoring and statistics

### 💾 Persistent Memory
- **Persistent Memory**: JSON-based storage for context retention
- **Vector Memory**: Semantic search using text similarity
- Automatic memory decay and cleanup
- Cross-session context retention

### 🌐 A2A HTTP Server
- RESTful API for external system integration
- Task submission via HTTP POST
- Agent message passing
- Real-time status monitoring

### 🔧 MCP (Model Context Protocol)
- Unified tool registry
- Category-based tool filtering
- Execution logging and statistics

## Installation

### Prerequisites
- Python 3.9+
- pip

### Setup

```bash
# Clone or extract the project
cd synapse

# Install dependencies
pip install -r requirements.txt

# Configure API keys
# Edit .env file and add your keys:
# GROQ_API_KEY=your_groq_key
# GEMINI_API_KEY=your_gemini_key (optional)
```

### Running

```bash
# Windows
synapse.bat

# Mac/Linux
chmod +x synapse.sh
./synapse.sh

# Or directly
python cli.py
```

## Usage

### CLI Commands

| Key | Action |
|-----|--------|
| `1` | Execute a task |
| `2` | View agent tools |
| `3` | System status |
| `4` | LLM Pool status |
| `5` | Memory search |
| `6` | Toggle A2A Server |
| `h` | Help |
| `q` | Quit |

### Task Examples

```
# File operations
write a poem about the ocean and save it to poem.txt
create folder Projects on Desktop with readme.txt inside
list files in Documents

# Content generation
write a haiku about coding
summarize this text: <your text>

# Web operations
fetch https://example.com and summarize it
download https://example.com/file.pdf to Downloads

# System operations
get system information and save to sysinfo.txt
what time is it
calculate 25 * 4 + sqrt(16)
```

### A2A Server API

Start the server from menu option `6`, then:

```bash
# Check health
curl http://127.0.0.1:8765/health

# Get status
curl http://127.0.0.1:8765/status

# Submit a task
curl -X POST http://127.0.0.1:8765/task \
  -H "Content-Type: application/json" \
  -d '{"task": "get system info"}'

# Send a message to an agent
curl -X POST http://127.0.0.1:8765/message \
  -H "Content-Type: application/json" \
  -d '{"recipient": "file_agent", "type": "task_request", "payload": {"tool": "list_directory", "args": {"directory": "."}}}'
```

## Project Structure

```
synapse/
├── cli.py                      # CLI Interface
├── synapse.py                  # Main orchestration
├── config.py                   # Configuration
├── requirements.txt
├── .env                        # API keys
├── synapse.bat / synapse.sh    # Launchers
├── README.md
│
├── llm/                        # LLM Abstraction Layer
│   ├── __init__.py
│   ├── base_llm.py            # Base LLM interface
│   ├── groq_llm.py            # Groq implementation
│   ├── gemini_llm.py          # Gemini implementation
│   └── llm_pool.py            # Pool manager with fallback
│
├── core/                       # Core Services
│   ├── __init__.py
│   ├── dag.py                 # DAG data structure
│   ├── dag_executor.py        # Parallel DAG executor
│   └── a2a_bus.py             # Message bus
│
├── agents/                     # Agent Implementations
│   ├── __init__.py
│   ├── base_agent.py          # Base agent class
│   ├── interaction_agent.py   # User interface
│   ├── planner_agent.py       # Plan creation
│   ├── orchestrator_agent.py  # Task orchestration
│   ├── file_agent.py          # File operations
│   ├── content_agent.py       # Content generation
│   ├── web_agent.py           # Web operations
│   └── system_agent.py        # System operations
│
├── memory/                     # Persistence
│   ├── __init__.py
│   └── persistent_memory.py   # Memory systems
│
├── mcp/                        # Tool Registry
│   ├── __init__.py
│   └── server.py              # MCP server
│
├── server/                     # HTTP API
│   ├── __init__.py
│   └── a2a_server.py          # A2A HTTP server
│
├── tools/                      # Tool Implementations
│   ├── __init__.py
│   └── all_tools.py           # All tools
│
└── memory_store/               # Memory data (auto-created)
    ├── persistent_memory.json
    └── vector_memory.json
```

## Configuration

### Environment Variables (.env)

```bash
# Required (at least one)
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key

# Optional
LOG_LEVEL=INFO
```

### config.py Settings

```python
# LLM Configuration
GROQ_MODEL = "llama-3.1-8b-instant"
GEMINI_MODEL = "gemini-2.0-flash"
LLM_PRIORITY = ["groq", "gemini"]

# DAG Execution
DAG_MAX_WORKERS = 4
DAG_TASK_TIMEOUT = 60

# A2A Server
A2A_SERVER_HOST = "127.0.0.1"
A2A_SERVER_PORT = 8765

# Memory
MEMORY_MAX_ENTRIES = 1000
```

## How It Works

### Request Flow

1. **User Input** → Interaction Agent interprets natural language
2. **Planning** → Planner Agent creates a DAG of tasks
3. **Validation** → DAG validated for cycles and missing dependencies
4. **Execution** → Orchestrator executes tasks in parallel where possible
5. **Results** → Results aggregated and formatted for display

### Parallel Execution Example

For a request like "fetch 3 websites and summarize each":

```
Level 0 (Parallel):     Level 1 (Parallel):
┌─────────────┐         ┌─────────────┐
│ Fetch URL 1 │────────▶│ Summarize 1 │
└─────────────┘         └─────────────┘
┌─────────────┐         ┌─────────────┐
│ Fetch URL 2 │────────▶│ Summarize 2 │
└─────────────┘         └─────────────┘
┌─────────────┐         ┌─────────────┐
│ Fetch URL 3 │────────▶│ Summarize 3 │
└─────────────┘         └─────────────┘

All fetches run in parallel (Level 0)
All summaries run in parallel (Level 1)
Each summary depends on its fetch completing
```

### LLM Fallback

```
Request → Try Groq (Primary)
              │
              ├─ Success → Return result
              │
              └─ Failure → Try Gemini (Fallback)
                               │
                               ├─ Success → Return result
                               │
                               └─ Failure → Return error
```

## Extending

### Adding a New Tool

1. Add function to `tools/all_tools.py`:
```python
def my_new_tool(arg1: str, arg2: int) -> Dict[str, Any]:
    try:
        # Your implementation
        return {"success": True, "result": "..."}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

2. Register in `register_all_tools()`:
```python
ToolDefinition("my_new_tool", "Description", ToolCategory.SYSTEM,
              my_new_tool, ["arg1", "arg2"])
```

### Adding a New LLM Provider

1. Create `llm/my_provider.py` extending `BaseLLM`
2. Implement `provider_name` property and `_call_api` method
3. Register in `llm_pool.py`

### Adding a New Agent

1. Create `agents/my_agent.py` extending `BaseAgent`
2. Define capabilities and tool categories
3. Implement `handle_task` and `handle_message`
4. Register with orchestrator

## Troubleshooting

### "No LLMs available"
- Ensure at least one API key is set in `.env`
- Check API key validity

### Tasks timing out
- Increase `DAG_TASK_TIMEOUT` in `config.py`
- Check network connectivity for web tasks

### Memory not persisting
- Check write permissions for `memory_store/` directory
- Memory only persists between sessions if stored successfully

## API Comparison

| Feature | Synapse v2 | v1 |
|---------|------------|-----|
| LLM Providers | Multiple + Fallback | Single |
| Execution | Parallel DAG | Sequential |
| Memory | Persistent + Vector | None |
| External API | A2A HTTP Server | None |
| Architecture | Microservice-based | Monolithic |

## License

MIT License - See LICENSE file

## Credits

Built with:
- [Groq](https://groq.com/) - Fast LLM inference
- [Google Gemini](https://deepmind.google/technologies/gemini/) - Advanced LLM
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment management

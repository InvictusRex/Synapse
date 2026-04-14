# Synapse - Multi-Agent System

A true multi-agent system with Agent-to-Agent (A2A) communication and Model Context Protocol (MCP) tool abstraction.

## Architecture

```
User Input
    │
    ▼
┌─────────────────────┐
│  Interaction Agent  │  ← Parses input, formats results
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Planner Agent     │  ← Creates execution DAG
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Orchestrator Agent  │  ← Dispatches & coordinates
└──────────┬──────────┘
           │
    ┌──────┼──────┬──────────┐
    ▼      ▼      ▼          ▼
┌──────┐┌──────┐┌──────┐┌──────┐
│ File ││Content││ Web  ││System│  ← Worker Agents
│Agent ││Agent ││Agent ││Agent │
└──┬───┘└──┬───┘└──┬───┘└──┬───┘
   │       │       │       │
   └───────┴───────┴───────┘
           │
           ▼
    ┌──────────────┐
    │ A2A Message  │  ← Inter-agent communication
    │     Bus      │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  MCP Server  │  ← Tool registry & execution
    └──────────────┘
```

## Key Components

### 1. A2A Message Bus (`core/a2a_bus.py`)
- Central communication hub for all agents
- Message types: TASK_REQUEST, TASK_RESULT, TOOL_REQUEST, etc.
- Agents don't call each other directly - all communication via bus

### 2. MCP Server (`mcp/server.py`)
- Tool registration with schemas
- Tool discovery and validation
- Standardized tool execution interface

### 3. Base Agent (`agents/base_agent.py`)
- Every agent has its own LLM for reasoning
- `think()` - Use LLM to reason about situations
- `decide_action()` - Autonomous decision making
- `use_tool()` - Execute tools via MCP
- `send_message()` / `receive_message()` - A2A communication

### 4. Specialized Agents

| Agent | Responsibility | Tools |
|-------|---------------|-------|
| **Interaction Agent** | Parse input, format output | None (meta) |
| **Planner Agent** | Create execution plans | None (meta) |
| **Orchestrator Agent** | Coordinate execution | None (meta) |
| **File Agent** | File operations | read_file, write_file, list_directory, etc. |
| **Content Agent** | Content generation | generate_text, summarize_text |
| **Web Agent** | Web operations | fetch_webpage, download_file |
| **System Agent** | System operations | run_command, get_system_info, calculate |

## How It Works

1. **User Input** → "Write an article about AI and save it to Desktop"

2. **Interaction Agent** parses:
   ```json
   {
     "intent": "Create and save content",
     "task_type": "content_generation",
     "entities": {"topics": ["AI"], "paths": ["Desktop"]}
   }
   ```

3. **Planner Agent** creates DAG:
   ```json
   {
     "tasks": [
       {"task_id": "T1", "agent": "content_agent", "tool": "generate_text", "args": {"prompt": "..."}},
       {"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {"content": "{T1.content}"}, "depends_on": ["T1"]}
     ]
   }
   ```

4. **Orchestrator Agent** executes:
   - Sends TASK_REQUEST to content_agent via A2A bus
   - Waits for TASK_RESULT
   - Resolves `{T1.content}` reference
   - Sends TASK_REQUEST to file_agent
   - Aggregates results

5. **Result** returned to user

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (Windows PowerShell)
$env:GROQ_API_KEY="your-groq-api-key"

# Set API key (Linux/Mac)
export GROQ_API_KEY="your-groq-api-key"

# Run CLI (recommended)
python cli.py

# Or run Web UI
streamlit run app.py
```

## CLI Interface

The CLI provides a beautiful terminal interface with Gruvbox-dark theme:

```
███████╗██╗   ██╗███╗   ██╗ █████╗ ██████╗ ███████╗███████╗
██╔════╝╚██╗ ██╔╝████╗  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
███████╗ ╚████╔╝ ██╔██╗ ██║███████║██████╔╝███████╗█████╗  
╚════██║  ╚██╔╝  ██║╚██╗██║██╔══██║██╔═══╝ ╚════██║██╔══╝  
███████║   ██║   ██║ ╚████║██║  ██║██║     ███████║███████╗
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝

[1] Execute a task
[2] View agent tools  
[3] System status
[h] Help
[q] Quit
```

### CLI Commands
- **[1]** - Enter task execution mode
- **[2]** - Browse tools by category (file, web, system, content, data)
- **[3]** - View system status and agent info
- **[h]** - Show help
- **[q]** - Quit
- Or just type your request directly!

## What Makes This a TRUE Multi-Agent System

1. **Each agent has its own LLM** - Not just tools, actual reasoning
2. **A2A Message Bus** - Agents communicate via messages, not direct calls
3. **MCP Protocol** - Standardized tool interface with schemas
4. **Autonomous decisions** - Agents decide how to accomplish tasks
5. **Non-hardcoded flow** - Plans are generated dynamically
6. **Dependency management** - Tasks can depend on other tasks' results

## Example Flow

```
[User] "List files on my Desktop"

[Interaction Agent] Parsing input...
  → {"intent": "list_directory", "task_type": "file_operation"}

[Planner Agent] Creating plan...
  → Task T1: file_agent.list_directory(~/Desktop)

[Orchestrator] Dispatching T1 to file_agent...
  → [A2A Bus] orchestrator → file_agent: TASK_REQUEST

[File Agent] Received task, using tool list_directory
  → [MCP Server] Executing list_directory
  → [A2A Bus] file_agent → orchestrator: TASK_RESULT

[Orchestrator] Task completed, aggregating results...

[Interaction Agent] Formatting result...
  → "Here are the files on your Desktop: ..."

[User] ← Final result
```

## Files

```
synapse/
├── cli.py                    # CLI Interface (Gruvbox theme)
├── app.py                    # Streamlit Web UI
├── synapse.py                # Main system (initializes everything)
├── config.py                 # Configuration
├── requirements.txt
│
├── core/
│   ├── a2a_bus.py           # A2A Message Bus
│   └── __init__.py
│
├── mcp/
│   ├── server.py            # MCP Server
│   └── __init__.py
│
├── tools/
│   ├── all_tools.py         # Tool implementations
│   └── __init__.py
│
└── agents/
    ├── base_agent.py        # Base Agent class
    ├── interaction_agent.py # User interaction
    ├── planner_agent.py     # Plan creation
    ├── orchestrator_agent.py# Execution coordination
    ├── file_agent.py        # File operations
    ├── content_agent.py     # Content generation
    ├── web_agent.py         # Web operations
    ├── system_agent.py      # System operations
    └── __init__.py
```

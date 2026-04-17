#Synapse 
[[Synapse]]
# Synapse Technical Documentation

## A Comprehensive Guide to the Multi-Agent AI System Architecture

---

## Table of Contents

1. [Introduction](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#1-introduction)
2. [System Overview](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#2-system-overview)
3. [Core Architecture](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#3-core-architecture)
4. [The Agent System](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#4-the-agent-system)
5. [Task Planning & DAG Execution](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#5-task-planning--dag-execution)
6. [Parallel Execution Engine](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#6-parallel-execution-engine)
7. [LLM Pool & Provider Management](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#7-llm-pool--provider-management)
8. [Memory System](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#8-memory-system)
9. [Tool System & MCP](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#9-tool-system--mcp)
10. [Agent-to-Agent Communication (A2A)](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#10-agent-to-agent-communication-a2a)
11. [External API Server](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#11-external-api-server)
12. [Data Flow & Request Lifecycle](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#12-data-flow--request-lifecycle)
13. [Error Handling & Recovery](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#13-error-handling--recovery)
14. [Configuration System](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#14-configuration-system)
15. [File Structure Reference](https://claude.ai/chat/c2ad0522-5e16-451f-9bc4-7ad7c199c375#15-file-structure-reference)

---

## 1. Introduction

### What is Synapse?

Synapse is a **multi-agent AI orchestration system** that transforms natural language requests into executable actions. Unlike traditional chatbots that simply respond with text, Synapse actually performs tasks on your computer - creating files, running commands, generating content, and more.

### The Agentic AI Paradigm

Traditional AI systems operate in a simple request-response pattern:

```
User: "How do I create a file?"
AI: "You can create a file by using the following command..."
```

Agentic AI systems operate in a goal-action pattern:

```
User: "Create a file called notes.txt with my meeting notes"
AI: [Analyzes request] → [Plans tasks] → [Executes file creation] → [Confirms completion]
```

The fundamental shift is from **informing** to **doing**.

### Design Principles

Synapse is built on several key principles:

1. **Modularity**: Each component is independent and replaceable
2. **Extensibility**: New agents and tools can be added without modifying core code
3. **Resilience**: Multiple LLM providers with automatic failover
4. **Transparency**: Full execution logs and task state visibility
5. **Parallelism**: Independent tasks execute concurrently for speed

---

## 2. System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                                 (cli.py)                                     │
│                         Rich terminal interface                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SYNAPSE CORE                                      │
│                            (synapse.py)                                      │
│                    Main orchestrator & coordinator                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│    AGENT LAYER      │   │    CORE SERVICES    │   │   INFRASTRUCTURE    │
│                     │   │                     │   │                     │
│ • Interaction Agent │   │ • DAG Builder       │   │ • LLM Pool          │
│ • Planner Agent     │   │ • DAG Executor      │   │ • Memory System     │
│ • File Agent        │   │ • A2A Bus           │   │ • MCP Server        │
│ • Content Agent     │   │                     │   │ • A2A Server        │
│ • System Agent      │   │                     │   │                     │
│ • Web Agent         │   │                     │   │                     │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL LAYER                                      │
│                           (tools/all_tools.py)                               │
│     Actual implementations: file ops, system commands, web requests          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Summary

|Component|File|Purpose|
|---|---|---|
|CLI|`cli.py`|User interface, input handling, output formatting|
|Synapse Core|`synapse.py`|Main orchestrator, initializes all components|
|Agents|`agents/*.py`|Specialized AI workers for different task types|
|DAG|`core/dag.py`|Task graph data structure|
|DAG Executor|`core/dag_executor.py`|Executes task graphs with parallelism|
|A2A Bus|`core/a2a_bus.py`|Inter-agent communication|
|LLM Pool|`llm/llm_pool.py`|Multi-provider LLM management|
|Memory|`memory/persistent_memory.py`|Persistent storage & vector search|
|MCP Server|`mcp/server.py`|Tool registry and execution|
|Tools|`tools/all_tools.py`|Actual tool implementations|
|A2A Server|`server/a2a_server.py`|External HTTP API|

---

## 3. Core Architecture

### The Synapse Class (synapse.py)

The `Synapse` class is the central coordinator that initializes and connects all system components.

```python
class Synapse:
    def __init__(self):
        # Infrastructure
        self.llm_pool = LLMPool()           # Multi-provider LLM management
        self.memory = PersistentMemory()     # Persistent storage
        self.mcp_server = MCPServer()        # Tool registry
        self.a2a_bus = A2ABus()              # Agent communication
        
        # Agents
        self.agents = {
            "interaction": InteractionAgent(),
            "planner": PlannerAgent(),
            "orchestrator": OrchestratorAgent(),
            "file": FileAgent(),
            "content": ContentAgent(),
            "system": SystemAgent(),
            "web": WebAgent(),
        }
        
        # Executor
        self.dag_executor = DAGExecutor()
```

### Initialization Flow

```
1. Load environment variables (.env)
         │
         ▼
2. Initialize LLM Pool
   ├── Connect to Groq API
   └── Connect to Gemini API (if key present)
         │
         ▼
3. Initialize Memory System
   ├── Load persistent_memory.json
   └── Load vector_memory.json
         │
         ▼
4. Initialize MCP Server
   └── Register all tools from tools/all_tools.py
         │
         ▼
5. Initialize A2A Bus
   └── Set up message routing
         │
         ▼
6. Initialize Agents
   └── Each agent registers with A2A bus
         │
         ▼
7. Initialize DAG Executor
   └── Connect to agents and tools
         │
         ▼
8. System Ready
```

---

## 4. The Agent System

### What is an Agent?

An agent is a specialized AI worker designed to handle a specific category of tasks. Each agent:

- Has a defined set of tools it can use
- Receives tasks via the A2A bus
- Executes tasks using the MCP server
- Returns results through the A2A bus

### Agent Hierarchy

```
                    ┌─────────────────────┐
                    │   Interaction Agent │  ← Entry point (parses user input)
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Planner Agent    │  ← Creates execution plan
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Orchestrator Agent  │  ← Coordinates execution
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   File Agent    │  │  Content Agent  │  │  System Agent   │
│                 │  │                 │  │                 │
│ • read_file     │  │ • generate_text │  │ • get_datetime  │
│ • write_file    │  │ • summarize     │  │ • get_sys_info  │
│ • create_folder │  │                 │  │ • calculate     │
│ • list_dir      │  │                 │  │ • run_command   │
│ • delete_file   │  │                 │  │                 │
│ • move_file     │  │                 │  │                 │
│ • copy_file     │  │                 │  │                 │
│ • search_files  │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         └─────────────────────┴─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Web Agent       │
                    │                     │
                    │ • fetch_webpage     │
                    │ • download_file     │
                    └─────────────────────┘
```

### Agent Descriptions

#### Interaction Agent

**Purpose**: First point of contact for user requests

**Responsibilities**:

- Parse natural language input
- Extract intent (what the user wants to do)
- Extract entities (files, paths, names, etc.)
- Determine if clarification is needed

**Example**:

```
Input: "create a file called notes.txt on my desktop"
Output: {
    "intent": "create_file",
    "entities": {
        "filename": "notes.txt",
        "location": "Desktop"
    }
}
```

#### Planner Agent

**Purpose**: Creates execution plans from parsed requests

**Responsibilities**:

- Analyze the request requirements
- Break down complex requests into atomic tasks
- Assign each task to the appropriate agent
- Define task dependencies
- Generate a DAG (Directed Acyclic Graph)

**Example**:

```
Input: "Write a poem about AI and save it to poem.txt"
Output: DAG with tasks:
  T1: generate_text (content_agent) - "Write a poem about AI"
  T2: write_file (file_agent) - Save to poem.txt [depends on T1]
```

**The Planner Prompt**: The planner uses a carefully crafted prompt that includes:

- Available tools and their required arguments
- User's system paths (Desktop, Documents, etc.)
- Examples of correct task planning
- JSON output format specification

#### Orchestrator Agent

**Purpose**: Coordinates the execution of planned tasks

**Responsibilities**:

- Receive the DAG from the planner
- Pass it to the DAG executor
- Monitor execution progress
- Handle errors and retries
- Aggregate results

#### File Agent

**Purpose**: All file system operations

**Tools**:

|Tool|Description|Required Arguments|
|---|---|---|
|`read_file`|Read file contents|`filepath`|
|`write_file`|Write/overwrite file|`filepath`, `content`|
|`create_file`|Create new file|`filepath`, `content` (optional)|
|`create_folder`|Create directory|`path`|
|`list_directory`|List folder contents|`path`|
|`delete_file`|Delete a file|`filepath`|
|`delete_folder`|Delete a directory|`path`|
|`move_file`|Move file/folder|`source`, `destination`|
|`copy_file`|Copy file/folder|`source`, `destination`|
|`search_files`|Search by pattern|`directory`, `pattern`|

#### Content Agent

**Purpose**: AI-powered content generation

**Tools**:

|Tool|Description|Required Arguments|
|---|---|---|
|`generate_text`|Generate text using LLM|`prompt`|
|`summarize_text`|Summarize given text|`text`|

**How it works**:

1. Receives a content generation request
2. Calls the LLM Pool to get an available LLM
3. Sends the prompt to the LLM
4. Returns the generated content

#### System Agent

**Purpose**: System operations and utilities

**Tools**:

|Tool|Description|Required Arguments|
|---|---|---|
|`get_datetime`|Get current date/time|None|
|`get_system_info`|Get system details|None|
|`calculate`|Math calculations|`expression`|
|`run_command`|Execute shell command|`command`|

#### Web Agent

**Purpose**: Internet operations

**Tools**:

|Tool|Description|Required Arguments|
|---|---|---|
|`fetch_webpage`|Get webpage content|`url`|
|`download_file`|Download from URL|`url`, `destination`|

### Base Agent Class

All agents inherit from `BaseAgent`:

```python
class BaseAgent:
    def __init__(self, name: str, tools: List[str]):
        self.name = name
        self.tools = tools
        self.llm_pool = None  # Injected by Synapse
        self.mcp_server = None  # Injected by Synapse
    
    async def execute_tool(self, tool_name: str, args: dict) -> dict:
        """Execute a tool via the MCP server"""
        return await self.mcp_server.execute(tool_name, args)
    
    async def get_llm_response(self, prompt: str) -> str:
        """Get a response from the LLM pool"""
        llm = self.llm_pool.get_available()
        return await llm.generate(prompt)
```

---

## 5. Task Planning & DAG Execution

### What is a DAG?

DAG stands for **Directed Acyclic Graph**. In Synapse:

- **Directed**: Tasks have a specific order (A must complete before B)
- **Acyclic**: No circular dependencies (prevents infinite loops)
- **Graph**: Tasks are nodes, dependencies are edges

### DAG Structure

```python
class DAGTask:
    task_id: str          # Unique identifier (T1, T2, etc.)
    agent: str            # Which agent executes this
    tool: str             # Which tool to use
    args: dict            # Arguments for the tool
    description: str      # Human-readable description
    depends_on: List[str] # Task IDs this depends on
    status: TaskStatus    # pending, running, completed, failed, skipped
    result: Any           # Output after execution
    error: str            # Error message if failed

class DAG:
    plan_id: str          # Unique plan identifier
    description: str      # What this plan accomplishes
    tasks: Dict[str, DAGTask]  # All tasks in the plan
```

### Visual Example

**Request**: "Get the current time, list my Desktop, and write a summary to report.txt"

```
                    ┌─────────────────┐
                    │   T1: get_time  │
                    │  (system_agent) │
                    │   depends: []   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    │                    ▼
┌───────────────┐            │           ┌───────────────┐
│ T2: list_dir  │            │           │ T3: list_docs │
│ (file_agent)  │            │           │ (file_agent)  │
│ depends: []   │            │           │ depends: []   │
└───────┬───────┘            │           └───────┬───────┘
        │                    │                   │
        └────────────────────┼───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ T4: write_file  │
                    │  (file_agent)   │
                    │ depends: [T1,   │
                    │   T2, T3]       │
                    └─────────────────┘

Execution Order:
- Wave 1: T1, T2, T3 (parallel - no dependencies)
- Wave 2: T4 (waits for T1, T2, T3)
```

### The Planning Process

```
1. User Request
   "Write a poem and save it to Desktop"
              │
              ▼
2. Interaction Agent
   Extracts: intent=create_content_and_save
             content_type=poem
             destination=Desktop
              │
              ▼
3. Planner Agent
   Receives parsed request
   Queries LLM with planning prompt
   LLM returns JSON task plan
              │
              ▼
4. DAG Construction
   {
     "tasks": [
       {
         "task_id": "T1",
         "agent": "content_agent",
         "tool": "generate_text",
         "args": {"prompt": "Write a poem about..."},
         "depends_on": []
       },
       {
         "task_id": "T2",
         "agent": "file_agent",
         "tool": "write_file",
         "args": {"filepath": "Desktop/poem.txt", "content": "{T1.output}"},
         "depends_on": ["T1"]
       }
     ]
   }
              │
              ▼
5. DAG Validation
   - Check all referenced agents exist
   - Check all tools exist for agents
   - Verify no circular dependencies
   - Validate required arguments present
              │
              ▼
6. Ready for Execution
```

### DAG Executor

The DAG Executor is responsible for running the task graph efficiently.

```python
class DAGExecutor:
    async def execute(self, dag: DAG) -> ExecutionResult:
        # 1. Topological sort to find execution waves
        waves = self.compute_execution_waves(dag)
        
        # 2. Execute each wave
        for wave in waves:
            # Tasks in same wave have no dependencies on each other
            # Execute them in parallel
            results = await asyncio.gather(*[
                self.execute_task(task) for task in wave
            ])
            
            # 3. Check for failures
            for task, result in zip(wave, results):
                if result.failed:
                    # Mark dependent tasks as skipped
                    self.skip_dependents(dag, task.task_id)
        
        # 4. Return aggregated results
        return self.aggregate_results(dag)
```

---

## 6. Parallel Execution Engine

### Why Parallelism?

Sequential execution:

```
T1 (2s) → T2 (2s) → T3 (2s) → T4 (2s) = 8 seconds total
```

Parallel execution (T1, T2, T3 are independent):

```
┌─ T1 (2s) ─┐
├─ T2 (2s) ─┼─→ T4 (2s) = 4 seconds total
└─ T3 (2s) ─┘
```

### Execution Waves

The executor groups tasks into "waves" based on dependencies:

```python
def compute_execution_waves(self, dag: DAG) -> List[List[DAGTask]]:
    waves = []
    remaining = set(dag.tasks.keys())
    completed = set()
    
    while remaining:
        # Find tasks whose dependencies are all completed
        ready = [
            dag.tasks[tid] for tid in remaining
            if all(dep in completed for dep in dag.tasks[tid].depends_on)
        ]
        
        if not ready:
            raise CyclicDependencyError()
        
        waves.append(ready)
        for task in ready:
            remaining.remove(task.task_id)
            completed.add(task.task_id)
    
    return waves
```

### Parallel Execution with asyncio

```python
async def execute_wave(self, wave: List[DAGTask]) -> List[TaskResult]:
    """Execute all tasks in a wave concurrently"""
    
    # Create coroutines for each task
    coroutines = [self.execute_single_task(task) for task in wave]
    
    # Run all concurrently and wait for all to complete
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    
    return results
```

### Dependency Resolution

When a task depends on another task's output:

```json
{
  "task_id": "T2",
  "tool": "write_file",
  "args": {
    "filepath": "poem.txt",
    "content": "{T1.output}"  // Reference to T1's output
  },
  "depends_on": ["T1"]
}
```

The executor resolves `{T1.output}` before executing T2:

```python
def resolve_references(self, task: DAGTask, completed_results: dict) -> dict:
    """Replace task references with actual values"""
    resolved_args = {}
    
    for key, value in task.args.items():
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            # Extract reference: {T1.output} -> T1
            ref_task_id = value[1:-1].split(".")[0]
            ref_result = completed_results[ref_task_id]
            resolved_args[key] = ref_result.output
        else:
            resolved_args[key] = value
    
    return resolved_args
```

---

## 7. LLM Pool & Provider Management

### What is the LLM Pool?

The LLM Pool manages multiple Language Model providers, providing:

- **Abstraction**: Agents don't need to know which LLM they're using
- **Failover**: Automatic switching if a provider fails
- **Load balancing**: Distribute requests across providers
- **Cost optimization**: Use cheaper/free providers when possible

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         LLM Pool                             │
│                       (llm_pool.py)                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Provider Registry                     │ │
│  │                                                          │ │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │ │
│  │   │    Groq     │   │   Gemini    │   │   OpenAI    │   │ │
│  │   │  (Primary)  │   │  (Backup)   │   │  (Future)   │   │ │
│  │   │             │   │             │   │             │   │ │
│  │   │ llama-3.3   │   │ gemini-2.0  │   │  gpt-4      │   │ │
│  │   │   -70b      │   │   -flash    │   │             │   │ │
│  │   └─────────────┘   └─────────────┘   └─────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Methods:                                                    │
│  • get_available() → Returns best available LLM             │
│  • generate(prompt) → Get response from pool                │
│  • get_status() → Health check all providers                │
└─────────────────────────────────────────────────────────────┘
```

### Provider Implementation

Each provider implements the `BaseLLM` interface:

```python
class BaseLLM(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this provider is currently available"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass
```

### Groq Provider

```python
class GroqLLM(BaseLLM):
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
    
    async def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2048)
        )
        return response.choices[0].message.content
    
    async def is_available(self) -> bool:
        try:
            # Quick health check
            await self.generate("Hi", max_tokens=5)
            return True
        except Exception:
            return False
```

### Gemini Provider

```python
class GeminiLLM(BaseLLM):
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.0-flash")
    
    async def generate(self, prompt: str, **kwargs) -> str:
        response = self.model.generate_content(prompt)
        return response.text
```

### Failover Logic

```python
class LLMPool:
    def __init__(self):
        self.providers = []
        
        # Add Groq (primary)
        if os.getenv("GROQ_API_KEY"):
            self.providers.append(GroqLLM())
        
        # Add Gemini (backup)
        if os.getenv("GEMINI_API_KEY"):
            self.providers.append(GeminiLLM())
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Try each provider until one succeeds"""
        last_error = None
        
        for provider in self.providers:
            try:
                if await provider.is_available():
                    return await provider.generate(prompt, **kwargs)
            except Exception as e:
                last_error = e
                continue  # Try next provider
        
        raise NoAvailableProviderError(last_error)
```

---

## 8. Memory System

### Overview

Synapse includes a persistent memory system that allows:

- **Key-Value Storage**: Store and retrieve facts
- **Vector Memory**: Semantic search using embeddings
- **Cross-Session Persistence**: Data survives restarts

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Memory System                           │
│                (memory/persistent_memory.py)                 │
│                                                              │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │   Key-Value Store   │    │      Vector Memory          │ │
│  │                     │    │                             │ │
│  │ "user_name": "John" │    │ Embeddings + Text           │ │
│  │ "project": "Alpha"  │    │                             │ │
│  │ "deadline": "May 1" │    │ [0.1, 0.5, ...] "Meeting"   │ │
│  │                     │    │ [0.3, 0.2, ...] "Project"   │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │ persistent_memory   │    │    vector_memory.json       │ │
│  │      .json          │    │                             │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
│                                                              │
│  memory_store/ directory                                    │
└─────────────────────────────────────────────────────────────┘
```

### Key-Value Memory

Simple fact storage and retrieval:

```python
class PersistentMemory:
    def __init__(self):
        self.store_path = "memory_store/persistent_memory.json"
        self.data = self._load()
    
    def store(self, key: str, value: Any) -> None:
        """Store a key-value pair"""
        self.data[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "type": type(value).__name__
        }
        self._save()
    
    def retrieve(self, key: str) -> Any:
        """Retrieve a value by key"""
        entry = self.data.get(key)
        return entry["value"] if entry else None
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair"""
        if key in self.data:
            del self.data[key]
            self._save()
            return True
        return False
    
    def list_keys(self) -> List[str]:
        """List all stored keys"""
        return list(self.data.keys())
```

### Vector Memory

Semantic search using cosine similarity:

```python
class VectorMemory:
    def __init__(self):
        self.store_path = "memory_store/vector_memory.json"
        self.entries = self._load()
    
    def add(self, text: str, metadata: dict = None) -> str:
        """Add text with auto-generated embedding"""
        embedding = self._compute_embedding(text)
        entry_id = str(uuid.uuid4())
        
        self.entries[entry_id] = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        self._save()
        return entry_id
    
    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """Search for similar entries"""
        query_embedding = self._compute_embedding(query)
        
        # Compute similarity scores
        scores = []
        for entry_id, entry in self.entries.items():
            similarity = self._cosine_similarity(
                query_embedding, 
                entry["embedding"]
            )
            scores.append((entry_id, entry, similarity))
        
        # Sort by similarity and return top-k
        scores.sort(key=lambda x: x[2], reverse=True)
        return [
            {"id": eid, "text": e["text"], "score": s, "metadata": e["metadata"]}
            for eid, e, s in scores[:top_k]
        ]
    
    def _compute_embedding(self, text: str) -> List[float]:
        """Simple TF-IDF based embedding (lightweight, no external API)"""
        # Tokenize and compute term frequencies
        words = text.lower().split()
        word_freq = Counter(words)
        
        # Create fixed-size embedding vector
        embedding = [0.0] * 100
        for word, freq in word_freq.items():
            # Hash word to index
            idx = hash(word) % 100
            embedding[idx] += freq
        
        # Normalize
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = sum(x * y for x, y in zip(a, b))
        return dot_product  # Vectors are already normalized
```

### Memory Integration with Agents

Agents can access memory through the Synapse core:

```python
# In an agent
async def execute(self, task):
    # Check memory for relevant context
    relevant = self.memory.search(task.description, top_k=3)
    
    # Include context in LLM prompt if relevant
    if relevant and relevant[0]["score"] > 0.7:
        context = "\n".join([r["text"] for r in relevant])
        prompt = f"Context:\n{context}\n\nTask: {task.description}"
    else:
        prompt = task.description
    
    # Execute with context
    result = await self.llm_pool.generate(prompt)
    
    # Store important results in memory
    if task.should_remember:
        self.memory.add(result, metadata={"task_id": task.task_id})
    
    return result
```

### Persistence Format

**persistent_memory.json**:

```json
{
  "user_name": {
    "value": "John",
    "timestamp": "2025-04-16T10:30:00",
    "type": "str"
  },
  "project_deadline": {
    "value": "2025-05-01",
    "timestamp": "2025-04-16T10:31:00",
    "type": "str"
  }
}
```

**vector_memory.json**:

```json
{
  "uuid-1234": {
    "text": "Meeting scheduled for Monday at 10am",
    "embedding": [0.1, 0.2, 0.3, ...],
    "metadata": {"source": "user_input"},
    "timestamp": "2025-04-16T10:30:00"
  }
}
```

---

## 9. Tool System & MCP

### Model Context Protocol (MCP)

MCP is a standardized protocol for AI systems to discover and use tools. Key concepts:

- **Tool Registry**: Central catalog of available tools
- **Tool Schema**: Description of inputs/outputs for each tool
- **Tool Execution**: Standardized way to invoke tools

### MCP Server Implementation

```python
class MCPServer:
    def __init__(self):
        self.tools = {}
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all tools from tools/all_tools.py"""
        from tools.all_tools import TOOLS
        
        for tool_name, tool_config in TOOLS.items():
            self.tools[tool_name] = {
                "function": tool_config["function"],
                "description": tool_config["description"],
                "parameters": tool_config["parameters"],
                "agent": tool_config["agent"]
            }
    
    def get_tools_for_agent(self, agent_name: str) -> List[dict]:
        """Get all tools available to a specific agent"""
        return [
            {
                "name": name,
                "description": config["description"],
                "parameters": config["parameters"]
            }
            for name, config in self.tools.items()
            if config["agent"] == agent_name
        ]
    
    async def execute(self, tool_name: str, args: dict) -> dict:
        """Execute a tool and return results"""
        if tool_name not in self.tools:
            raise ToolNotFoundError(tool_name)
        
        tool = self.tools[tool_name]
        
        # Validate arguments
        self._validate_args(tool["parameters"], args)
        
        # Execute
        try:
            result = await tool["function"](**args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### Tool Definition Format

Tools are defined in `tools/all_tools.py`:

```python
TOOLS = {
    "list_directory": {
        "function": list_directory,
        "description": "List contents of a directory",
        "parameters": {
            "path": {
                "type": "string",
                "description": "Directory path to list",
                "required": True
            }
        },
        "agent": "file_agent"
    },
    
    "create_file": {
        "function": create_file,
        "description": "Create a new file with optional content",
        "parameters": {
            "filepath": {
                "type": "string",
                "description": "Path for the new file",
                "required": True
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file",
                "required": False,
                "default": ""
            }
        },
        "agent": "file_agent"
    },
    
    "generate_text": {
        "function": generate_text,
        "description": "Generate text using AI",
        "parameters": {
            "prompt": {
                "type": "string",
                "description": "The prompt for text generation",
                "required": True
            }
        },
        "agent": "content_agent"
    }
}
```

### Tool Implementation Examples

```python
# File Operations
async def list_directory(path: str) -> dict:
    """List contents of a directory"""
    resolved_path = resolve_path(path)
    
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Directory not found: {path}")
    
    items = []
    for entry in os.scandir(resolved_path):
        item = {
            "name": entry.name,
            "type": "folder" if entry.is_dir() else "file",
            "size": format_size(entry.stat().st_size) if entry.is_file() else "-"
        }
        items.append(item)
    
    # Sort: folders first, then files
    items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
    
    return {
        "directory": resolved_path,
        "items": items,
        "count": len(items)
    }

async def create_file(filepath: str, content: str = "") -> dict:
    """Create a new file"""
    resolved_path = resolve_path(filepath)
    
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
    
    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return {
        "filepath": resolved_path,
        "size": len(content),
        "created": True
    }

# System Operations
async def get_datetime() -> dict:
    """Get current date and time"""
    now = datetime.now()
    return {
        "datetime": now.strftime("%A, %B %d, %Y at %I:%M:%S %p"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timestamp": now.timestamp()
    }

async def calculate(expression: str) -> dict:
    """Safely evaluate a math expression"""
    # Only allow safe characters
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expression):
        raise ValueError("Invalid characters in expression")
    
    result = eval(expression)  # Safe due to character whitelist
    return {
        "expression": expression,
        "result": result
    }
```

### Path Resolution

The tool system includes intelligent path resolution:

```python
def resolve_path(path: str) -> str:
    """Resolve user-friendly paths to actual system paths"""
    
    # Handle special locations
    home = os.path.expanduser("~")
    special_paths = {
        "desktop": os.path.join(home, "Desktop"),
        "documents": os.path.join(home, "Documents"),
        "downloads": os.path.join(home, "Downloads"),
        "home": home,
        "~": home
    }
    
    # Normalize path
    path = path.replace("\\", "/")
    lower_path = path.lower()
    
    # Check if starts with special location
    for key, value in special_paths.items():
        if lower_path.startswith(key):
            return path.replace(path[:len(key)], value, 1)
    
    # Handle relative paths
    if not os.path.isabs(path):
        return os.path.abspath(path)
    
    return path
```

---

## 10. Agent-to-Agent Communication (A2A)

### Overview

The A2A Bus enables agents to communicate with each other without direct coupling.

### Message Types

```python
class MessageType(Enum):
    TASK_REQUEST = "task_request"       # Request an agent to do something
    TASK_RESULT = "task_result"         # Result of a completed task
    TASK_ERROR = "task_error"           # Error during task execution
    STATUS_REQUEST = "status_request"   # Request agent status
    STATUS_RESPONSE = "status_response" # Agent status response
    BROADCAST = "broadcast"             # Message to all agents
```

### Message Structure

```python
@dataclass
class A2AMessage:
    id: str                    # Unique message ID
    type: MessageType          # Type of message
    sender: str                # Sending agent name
    recipient: str             # Receiving agent name (or "all" for broadcast)
    payload: dict              # Message content
    timestamp: datetime        # When message was sent
    correlation_id: str = None # Links related messages (request/response)
```

### A2A Bus Implementation

```python
class A2ABus:
    def __init__(self):
        self.subscribers = {}      # agent_name -> callback
        self.message_queue = asyncio.Queue()
        self.message_history = []  # For debugging
    
    def register(self, agent_name: str, callback: Callable):
        """Register an agent to receive messages"""
        self.subscribers[agent_name] = callback
    
    async def send(self, message: A2AMessage):
        """Send a message to an agent or broadcast"""
        self.message_history.append(message)
        
        if message.recipient == "all":
            # Broadcast to all agents
            for agent_name, callback in self.subscribers.items():
                if agent_name != message.sender:
                    await callback(message)
        else:
            # Send to specific agent
            if message.recipient in self.subscribers:
                await self.subscribers[message.recipient](message)
            else:
                raise AgentNotFoundError(message.recipient)
    
    async def request(self, sender: str, recipient: str, payload: dict) -> dict:
        """Send a request and wait for response"""
        correlation_id = str(uuid.uuid4())
        
        request = A2AMessage(
            id=str(uuid.uuid4()),
            type=MessageType.TASK_REQUEST,
            sender=sender,
            recipient=recipient,
            payload=payload,
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        # Create response future
        response_future = asyncio.Future()
        self._pending_requests[correlation_id] = response_future
        
        # Send request
        await self.send(request)
        
        # Wait for response
        response = await asyncio.wait_for(response_future, timeout=30.0)
        
        return response.payload
```

### Communication Flow Example

```
User: "Write a poem and save it"

1. CLI → Synapse
   User input received

2. Synapse → Interaction Agent (via A2A)
   Message: {type: TASK_REQUEST, payload: {input: "Write a poem..."}}

3. Interaction Agent → Planner Agent (via A2A)
   Message: {type: TASK_REQUEST, payload: {parsed: {intent: ..., entities: ...}}}

4. Planner Agent → Orchestrator Agent (via A2A)
   Message: {type: TASK_RESULT, payload: {dag: [T1, T2]}}

5. Orchestrator → Content Agent (via A2A)
   Message: {type: TASK_REQUEST, payload: {task: T1, tool: generate_text}}

6. Content Agent → Orchestrator (via A2A)
   Message: {type: TASK_RESULT, payload: {output: "Roses are red..."}}

7. Orchestrator → File Agent (via A2A)
   Message: {type: TASK_REQUEST, payload: {task: T2, tool: write_file, content: "..."}}

8. File Agent → Orchestrator (via A2A)
   Message: {type: TASK_RESULT, payload: {filepath: "Desktop/poem.txt"}}

9. Orchestrator → Synapse (via A2A)
   Message: {type: TASK_RESULT, payload: {success: true, results: [...]}}

10. Synapse → CLI
    Display results to user
```

---

## 11. External API Server

### Overview

The A2A Server provides an HTTP API for external applications to interact with Synapse.

### Endpoints

|Endpoint|Method|Description|
|---|---|---|
|`/health`|GET|Health check|
|`/status`|GET|System status|
|`/task`|POST|Submit a task|
|`/result/{task_id}`|GET|Get task result|

### Implementation

```python
class A2AServer:
    def __init__(self, synapse, host="127.0.0.1", port=8765):
        self.synapse = synapse
        self.host = host
        self.port = port
        self.server = None
        self._running = False
    
    async def start(self):
        """Start the HTTP server"""
        self._running = True
        self.server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port
        )
        asyncio.create_task(self._serve())
    
    async def handle_request(self, request: dict) -> dict:
        """Handle incoming HTTP requests"""
        path = request["path"]
        method = request["method"]
        
        if path == "/health" and method == "GET":
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        elif path == "/status" and method == "GET":
            return self.synapse.get_status()
        
        elif path == "/task" and method == "POST":
            task_input = request["body"]["task"]
            result = await self.synapse.execute(task_input)
            return result
        
        else:
            return {"error": "Not found", "status": 404}
```

### Usage Examples

**PowerShell**:

```powershell
# Health check
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health'

# Submit a task
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/task' `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"task": "what time is it"}'

# Get system status
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/status'
```

**Python**:

```python
import requests

# Submit a task
response = requests.post(
    "http://127.0.0.1:8765/task",
    json={"task": "list files on desktop"}
)
print(response.json())
```

**cURL**:

```bash
# Health check
curl http://127.0.0.1:8765/health

# Submit a task
curl -X POST http://127.0.0.1:8765/task \
  -H "Content-Type: application/json" \
  -d '{"task": "calculate 25 * 4"}'
```

---

## 12. Data Flow & Request Lifecycle

### Complete Request Lifecycle

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           REQUEST LIFECYCLE                                 │
└────────────────────────────────────────────────────────────────────────────┘

User Input: "Write a haiku about coding and save it to Desktop/haiku.txt"
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: INPUT PROCESSING                                                   │
│                                                                             │
│ CLI receives input                                                          │
│ └── Passes to Synapse.execute()                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: INTERACTION ANALYSIS                                               │
│                                                                             │
│ Interaction Agent analyzes request                                          │
│ └── Output: {                                                              │
│       "intent": "generate_and_save",                                       │
│       "entities": {                                                        │
│         "content_type": "haiku",                                           │
│         "topic": "coding",                                                 │
│         "destination": "Desktop/haiku.txt"                                 │
│       }                                                                    │
│     }                                                                      │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: TASK PLANNING                                                      │
│                                                                             │
│ Planner Agent creates DAG                                                   │
│ └── Calls LLM with planning prompt                                         │
│ └── Parses JSON response                                                   │
│ └── Output: DAG {                                                          │
│       tasks: [                                                             │
│         {id: "T1", agent: "content", tool: "generate_text",                │
│          args: {prompt: "Write a haiku about coding"}},                    │
│         {id: "T2", agent: "file", tool: "write_file",                      │
│          args: {filepath: "Desktop/haiku.txt", content: "{T1.output}"},    │
│          depends_on: ["T1"]}                                               │
│       ]                                                                    │
│     }                                                                      │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: DAG VALIDATION                                                     │
│                                                                             │
│ Validate DAG structure                                                      │
│ ├── Check all agents exist                                                 │
│ ├── Check all tools exist                                                  │
│ ├── Validate required arguments                                            │
│ └── Verify no circular dependencies                                        │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: WAVE COMPUTATION                                                   │
│                                                                             │
│ Compute execution waves                                                     │
│ └── Wave 1: [T1] (no dependencies)                                         │
│ └── Wave 2: [T2] (depends on T1)                                           │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 6: WAVE 1 EXECUTION                                                   │
│                                                                             │
│ Execute T1: generate_text                                                   │
│ ├── Content Agent receives task                                            │
│ ├── Calls LLM Pool for text generation                                     │
│ ├── LLM generates: "Code flows like water / Bugs hide in logic's depths /  │
│ │                   Debug, compile, run"                                   │
│ └── T1.status = completed, T1.result = haiku text                          │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 7: REFERENCE RESOLUTION                                               │
│                                                                             │
│ Resolve {T1.output} in T2.args                                             │
│ └── T2.args.content = "Code flows like water..."                           │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 8: WAVE 2 EXECUTION                                                   │
│                                                                             │
│ Execute T2: write_file                                                      │
│ ├── File Agent receives task                                               │
│ ├── Resolves path: Desktop/haiku.txt → C:\Users\...\Desktop\haiku.txt     │
│ ├── Writes content to file                                                 │
│ └── T2.status = completed, T2.result = {filepath: "...", created: true}   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 9: RESULT AGGREGATION                                                 │
│                                                                             │
│ Orchestrator aggregates results                                             │
│ └── Output: {                                                              │
│       success: true,                                                       │
│       tasks_completed: 2,                                                  │
│       tasks_failed: 0,                                                     │
│       parallel_execution: false,                                           │
│       task_states: {T1: {...}, T2: {...}},                                │
│       all_outputs: [{type: "generate_text", content: "..."}]              │
│     }                                                                      │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STAGE 10: OUTPUT DISPLAY                                                    │
│                                                                             │
│ CLI formats and displays results                                            │
│ ├── Shows success panel                                                    │
│ ├── Lists completed tasks with checkmarks                                  │
│ ├── Displays generated content                                             │
│ └── Shows file saved confirmation                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Error Handling & Recovery

### Error Types

```python
class SynapseError(Exception):
    """Base exception for all Synapse errors"""
    pass

class PlanningError(SynapseError):
    """Error during task planning"""
    pass

class ExecutionError(SynapseError):
    """Error during task execution"""
    pass

class ToolNotFoundError(SynapseError):
    """Requested tool doesn't exist"""
    pass

class AgentNotFoundError(SynapseError):
    """Requested agent doesn't exist"""
    pass

class LLMError(SynapseError):
    """Error from LLM provider"""
    pass

class ValidationError(SynapseError):
    """Invalid input or configuration"""
    pass
```

### Error Recovery Strategies

**1. LLM Failover**

```python
# If primary LLM fails, try backup
try:
    result = await groq.generate(prompt)
except GroqError:
    result = await gemini.generate(prompt)  # Automatic failover
```

**2. Task Retry**

```python
# Retry failed tasks up to 3 times
for attempt in range(3):
    try:
        result = await execute_task(task)
        break
    except TransientError:
        await asyncio.sleep(1 * attempt)  # Exponential backoff
```

**3. Graceful Degradation**

```python
# If a task fails, skip dependent tasks but continue others
if task.status == "failed":
    for dependent in get_dependents(task):
        dependent.status = "skipped"
        dependent.error = f"Skipped due to {task.task_id} failure"
```

**4. JSON Parsing Recovery**

```python
def parse_llm_json(response: str) -> dict:
    """Robust JSON parsing with recovery"""
    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try extracting JSON from markdown code blocks
    match = re.search(r'```json?\s*([\s\S]*?)\s*```', response)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try fixing common issues
    cleaned = response
    cleaned = re.sub(r'\\([^"\\nrtbf/])', r'\1', cleaned)  # Fix invalid escapes
    cleaned = cleaned.replace("'", '"')  # Single to double quotes
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise PlanningError(f"Could not parse LLM response as JSON")
```

---

## 14. Configuration System

### Environment Variables (.env)

```bash
# Required
GROQ_API_KEY=gsk_...          # Groq API key (primary LLM)

# Optional
GEMINI_API_KEY=...            # Google Gemini API key (backup LLM)
SYNAPSE_DEBUG=true            # Enable debug logging
SYNAPSE_LOG_LEVEL=INFO        # Log level: DEBUG, INFO, WARNING, ERROR
A2A_SERVER_PORT=8765          # External API server port
```

### Configuration File (config.py)

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM Settings
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # Server Settings
    A2A_SERVER_HOST = os.getenv("A2A_SERVER_HOST", "127.0.0.1")
    A2A_SERVER_PORT = int(os.getenv("A2A_SERVER_PORT", "8765"))
    
    # Memory Settings
    MEMORY_STORE_PATH = os.getenv("MEMORY_STORE_PATH", "memory_store")
    
    # Logging
    LOG_LEVEL = os.getenv("SYNAPSE_LOG_LEVEL", "INFO")
    DEBUG = os.getenv("SYNAPSE_DEBUG", "false").lower() == "true"
    
    # Execution
    MAX_TASK_RETRIES = int(os.getenv("MAX_TASK_RETRIES", "3"))
    TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "30"))
```

---

## 15. File Structure Reference

```
Synapse/
│
├── cli.py                      # Command-line interface
│   ├── main()                  # Entry point
│   ├── print_main_ui()         # Display main menu
│   ├── display_result()        # Format task results
│   ├── run_tests()             # Test system
│   └── Colors/Styles           # UI theming
│
├── synapse.py                  # Core orchestrator
│   ├── Synapse class           # Main coordinator
│   ├── initialize()            # Setup all components
│   ├── execute()               # Process user requests
│   └── get_status()            # System status
│
├── config.py                   # Configuration management
│
├── agents/                     # AI Agents
│   ├── __init__.py
│   ├── base_agent.py           # Base class for all agents
│   ├── interaction_agent.py    # Parse user input
│   ├── planner_agent.py        # Create execution plans
│   ├── orchestrator_agent.py   # Coordinate execution
│   ├── file_agent.py           # File operations
│   ├── content_agent.py        # AI content generation
│   ├── system_agent.py         # System operations
│   └── web_agent.py            # Web operations
│
├── core/                       # Core infrastructure
│   ├── __init__.py
│   ├── dag.py                  # DAG data structures
│   │   ├── DAGTask             # Single task
│   │   ├── DAG                 # Task graph
│   │   └── TaskStatus          # Status enum
│   ├── dag_executor.py         # Execute task graphs
│   │   ├── execute()           # Main execution
│   │   ├── compute_waves()     # Find parallel groups
│   │   └── resolve_refs()      # Handle dependencies
│   └── a2a_bus.py              # Agent communication
│       ├── register()          # Register agent
│       ├── send()              # Send message
│       └── request()           # Request/response
│
├── llm/                        # LLM providers
│   ├── __init__.py
│   ├── base_llm.py             # Abstract base class
│   ├── groq_llm.py             # Groq provider
│   ├── gemini_llm.py           # Gemini provider
│   └── llm_pool.py             # Multi-provider management
│       ├── get_available()     # Get best provider
│       ├── generate()          # Generate with failover
│       └── get_status()        # Provider health
│
├── memory/                     # Memory system
│   ├── __init__.py
│   └── persistent_memory.py
│       ├── PersistentMemory    # Key-value store
│       └── VectorMemory        # Semantic search
│
├── mcp/                        # Model Context Protocol
│   ├── __init__.py
│   └── server.py               # Tool registry
│       ├── register_tool()     # Add tool
│       ├── execute()           # Run tool
│       └── get_tools()         # List tools
│
├── tools/                      # Tool implementations
│   ├── __init__.py
│   └── all_tools.py
│       ├── TOOLS               # Tool registry
│       ├── resolve_path()      # Path helper
│       ├── list_directory()    # File tools
│       ├── create_file()
│       ├── get_datetime()      # System tools
│       ├── calculate()
│       ├── generate_text()     # Content tools
│       └── fetch_webpage()     # Web tools
│
├── server/                     # External API
│   ├── __init__.py
│   └── a2a_server.py
│       ├── start()             # Start server
│       ├── stop()              # Stop server
│       └── handle_request()    # Process HTTP
│
├── memory_store/               # Persistent data
│   ├── persistent_memory.json  # Key-value data
│   └── vector_memory.json      # Vector embeddings
│
├── logs/                       # Log files
│   └── .gitkeep
│
├── setup/                      # Setup scripts
│   └── .gitkeep
│
├── .env                        # Environment variables
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── synapse.bat                 # Windows launcher
├── synapse.sh                  # Unix launcher
└── README.md                   # User documentation
```

---

## Appendix A: Glossary

|Term|Definition|
|---|---|
|**Agent**|Specialized AI worker for a specific task category|
|**A2A**|Agent-to-Agent communication protocol|
|**DAG**|Directed Acyclic Graph - task execution structure|
|**LLM**|Large Language Model - AI that generates text|
|**MCP**|Model Context Protocol - tool interface standard|
|**Tool**|Specific capability an agent can execute|
|**Wave**|Group of tasks that can execute in parallel|
|**Failover**|Automatic switching to backup when primary fails|

---

## Appendix B: Adding New Components

### Adding a New Tool

1. Add function to `tools/all_tools.py`:

```python
async def my_new_tool(arg1: str, arg2: int = 10) -> dict:
    """Description of what this tool does"""
    # Implementation
    return {"result": "..."}
```

2. Register in TOOLS dictionary:

```python
TOOLS["my_new_tool"] = {
    "function": my_new_tool,
    "description": "What this tool does",
    "parameters": {
        "arg1": {"type": "string", "required": True},
        "arg2": {"type": "integer", "required": False, "default": 10}
    },
    "agent": "system_agent"  # Which agent owns this tool
}
```

### Adding a New Agent

1. Create `agents/new_agent.py`:

```python
from agents.base_agent import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="new_agent",
            tools=["tool1", "tool2"]
        )
    
    async def process(self, task):
        # Custom processing logic
        result = await self.execute_tool(task.tool, task.args)
        return result
```

2. Register in `synapse.py`:

```python
from agents.new_agent import NewAgent

self.agents["new"] = NewAgent()
```

### Adding a New LLM Provider

1. Create `llm/new_llm.py`:

```python
from llm.base_llm import BaseLLM

class NewLLM(BaseLLM):
    def __init__(self):
        self.client = NewProvider(api_key=os.getenv("NEW_API_KEY"))
    
    async def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.complete(prompt)
        return response.text
    
    async def is_available(self) -> bool:
        try:
            await self.generate("test", max_tokens=5)
            return True
        except:
            return False
    
    @property
    def name(self) -> str:
        return "new_provider"
```

2. Add to `llm/llm_pool.py`:

```python
if os.getenv("NEW_API_KEY"):
    self.providers.append(NewLLM())
```

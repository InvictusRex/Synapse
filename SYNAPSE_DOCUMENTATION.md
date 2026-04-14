# Synapse — System Documentation

> Multi-Agent Workflow System using A2A Communication and MCP-Inspired Tool Abstraction

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Module Reference](#4-module-reference)
5. [MCP-Inspired Tool System](#5-mcp-inspired-tool-system)
6. [Execution Flow](#6-execution-flow)
7. [A2A Communication Model](#7-a2a-communication-model)
8. [LLM Integration](#8-llm-integration)
9. [Directory Structure](#9-directory-structure)
10. [Configuration & Setup](#10-configuration--setup)
11. [Complete Walkthrough Example](#11-complete-walkthrough-example)
12. [Design Decisions](#12-design-decisions)
13. [Extending the System](#13-extending-the-system)

---

## 1. Project Overview

### What is Synapse?

Synapse is a **dynamic, multi-agent orchestration system** that takes natural language user requests, decomposes them into structured plans, and executes those plans through specialized agents that interact exclusively via a centralized tool server.

### Core Principles

| Principle                           | Description                                                                                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Dynamic Planning**                | No hardcoded workflows. The LLM-powered Planner generates execution steps at runtime based on user intent and available capabilities.            |
| **Tool Abstraction (MCP-Inspired)** | Agents never implement logic directly. All actions are performed through tools registered with a centralized MCP Tool Server.                    |
| **A2A Communication via Context**   | Agents do not communicate directly. All inter-agent data flow passes through a shared Context object, simulating Agent-to-Agent (A2A) protocols. |
| **Separation of Concerns**          | Planning, execution, and tool logic are fully decoupled into separate modules.                                                                   |
| **Loose Coupling**                  | Agents, tools, and the orchestrator can be modified, added, or replaced independently.                                                           |

### What Synapse Does

Given a natural language command like:

```
"Create a report on AI in healthcare and save it"
```

Synapse will:

1. **Analyze** the input to extract intent, topic, and output requirements
2. **Plan** a sequence of agent-tool steps dynamically
3. **Execute** each step through the orchestrator, routing to the correct agent
4. **Save** the result to a file on disk
5. **Report** the outcome and execution trace to the user

---

## 2. System Architecture

Synapse follows a **linear pipeline architecture** with five stages:

```
User Input → Context Analyzer → Planner Agent → Orchestrator → Output
```

Each stage transforms or acts on a **shared Context object** that carries all state through the pipeline. The Orchestrator dispatches work to **Agents**, which delegate to the **MCP Tool Server**, which executes **Tool Implementations**.

### Component Relationships

```
                        ┌──────────────────────────────────────────┐
                        │              LLM Provider                │
                        │   (Groq / OpenAI / Ollama / Any API)     │
                        └──────┬───────────┬──────────┬────────────┘
                               │           │          │
                    used by    │    used by│          │ used by
                               │           │          │
┌─────────┐    ┌───────────────▼──┐   ┌────▼─────┐   ┌▼──────────────┐
│  User   │───>│ Context Analyzer │──>│ Planner  │──>│  Orchestrator │
│  Input  │    │                  │   │  Agent   │   │               │
└─────────┘    └──────────────────┘   └──────────┘   └───────┬───────┘
                                                             │
                                                     dispatches steps
                                                             │
                                           ┌─────────────────┼─────────────────┐
                                           │                 │                 │
                                    ┌──────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
                                    │ ContentAgent│  │ SystemAgent  │  │  (Future)    │
                                    │             │  │              │  │  Agents...   │
                                    └──────┬──────┘  └───────┬──────┘  └──────────────┘
                                           │                 │
                                    delegates to      delegates to
                                           │                 │
                                    ┌──────▼─────────────────▼──────┐
                                    │       MCP Tool Server         │
                                    │   (validate → execute → return)│
                                    └──────────────┬────────────────┘
                                                   │
                                    ┌──────────────┼──────────────┐
                                    │              │              │
                              ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
                              │ generate  │ │ save_file │ │ open_file │
                              │ _report   │ │           │ │           │
                              └───────────┘ └───────────┘ └───────────┘
                                Content       System        System
                                 Tools         Tools         Tools
```

---

## 3. Architecture Diagram

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SHARED CONTEXT                              │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬────────┐  │
│  │raw_input │ intent   │ topic    │  plan    │  text    │ status │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┴────────┘  │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┬───────┘
       │          │          │          │          │          │
    written    written    written    written    written    written
    by         by         by         by         by         by
       │          │          │          │          │          │
  ┌────▼───┐ ┌────▼────┐ ┌──▼───┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼─────────┐
  │ main.py│ │Analyzer │ │Anal. │ │Planner │ │Content │ │Orchestrator│
  │        │ │         │ │      │ │        │ │Agent   │ │            │
  └────────┘ └─────────┘ └──────┘ └────────┘ └────────┘ └────────────┘
```

### Tool Invocation Sequence

```
  Orchestrator          Agent            MCPToolServer       ToolRegistry        Tool Function
      │                   │                    │                  │                    │
      │  execute(action,  │                    │                  │                    │
      │  params, context) │                    │                  │                    │
      │──────────────────>│                    │                  │                    │
      │                   │  execute_tool(     │                  │                    │
      │                   │  tool_name, params)│                  │                    │
      │                   │───────────────────>│                  │                    │
      │                   │                    │  get(tool_name)  │                    │
      │                   │                    │─────────────────>│                    │
      │                   │                    │  ToolDefinition  │                    │
      │                   │                    │<─────────────────│                    │
      │                   │                    │                  │                    │
      │                   │                    │  validate_params(schema, params)      │
      │                   │                    │──────────────────────────────>        │
      │                   │                    │                                      │
      │                   │                    │  tool.function(**params)              │
      │                   │                    │─────────────────────────────────────> │
      │                   │                    │                          result dict  │
      │                   │                    │<───────────────────────────────────── │
      │                   │    result dict     │                                      │
      │                   │<───────────────────│                                      │
      │    result dict    │                    │                                      │
      │<──────────────────│                    │                                      │
      │                   │                    │                                      │
      │  context.update(result)                │                                      │
      │                   │                    │                                      │
```

---

## 4. Module Reference

### 4.1 main.py — Entry Point

**Purpose:** Wires all components together and runs the full pipeline.

**What it does:**

1. Reads configuration from `.env` via `config.py`
2. Creates the `LLMClient` with the configured provider
3. Creates the `MCPToolServer` and registers all tools
4. Creates agents (`ContentAgent`, `SystemAgent`) and registers them
5. Runs the 4-stage pipeline: Analyze → Plan → Execute → Report

**How to run:**

```bash
python main.py                                          # interactive prompt
python main.py "Create a report on AI and save it"      # direct input
```

---

### 4.2 config.py — Configuration

**Purpose:** Loads settings from environment variables / `.env` file.

**Variables:**

| Variable       | Default                          | Description                                     |
| -------------- | -------------------------------- | ----------------------------------------------- |
| `LLM_API_KEY`  | (required)                       | API key for the LLM provider                    |
| `LLM_MODEL`    | `llama-3.3-70b-versatile`        | Model identifier                                |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Provider's API endpoint                         |
| `LOG_LEVEL`    | `INFO`                           | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

---

### 4.3 context_manager.py — Shared Context

**Purpose:** The single mutable state object that flows through the entire pipeline. This is the backbone of A2A communication.

**Class: `Context`**

| Method                       | Description                                 |
| ---------------------------- | ------------------------------------------- |
| `__init__(raw_input)`        | Initialize with the user's raw input string |
| `get(key, default)`          | Read a value from context                   |
| `set(key, value)`            | Write a value to context                    |
| `update(dict)`               | Merge a dictionary into context             |
| `add_trace(step_id, status)` | Record an execution trace entry             |
| `get_trace()`                | Return the full execution trace             |
| `snapshot()`                 | Deep copy of entire state (for logging)     |

**Initial state structure:**

```python
{
    "raw_input": "...",       # Original user input
    "intent": None,           # Extracted intent (set by Analyzer)
    "topic": None,            # Extracted topic (set by Analyzer)
    "doc_type": None,         # Document type (set by Analyzer)
    "output_mode": None,      # Delivery mode (set by Analyzer)
    "plan": [],               # Execution plan (set by Planner)
    "text": None,             # Generated content (set by ContentAgent)
    "status": "initialized",  # Pipeline status
}
```

**How data flows through context:**

```
main.py         sets: raw_input
Analyzer        sets: intent, topic, doc_type, output_mode
Planner         sets: plan
ContentAgent    sets: text
SystemAgent     sets: saved_path, status
Orchestrator    sets: status (executing/completed/failed), trace entries
```

---

### 4.4 context_analyzer.py — Intent Extraction

**Purpose:** Parse raw natural language input into a structured `AnalyzedIntent`.

**How it works:**

1. Sends the raw input to the LLM with a structured extraction prompt
2. The LLM returns JSON with `intent`, `topic`, `doc_type`, `output_mode`, `parameters`
3. Parses the JSON into an `AnalyzedIntent` dataclass
4. Includes fallback cleanup for markdown-fenced JSON responses

**Class: `ContextAnalyzer`**

- `analyze(raw_input: str) -> AnalyzedIntent`

**Dataclass: `AnalyzedIntent`**

```python
@dataclass
class AnalyzedIntent:
    intent: str           # e.g. "create_document"
    topic: str            # e.g. "AI in healthcare"
    doc_type: str         # e.g. "report"
    output_mode: str      # e.g. "file"
    parameters: dict      # extra key-value pairs
```

**Example transformation:**

```
Input:  "Create a report on AI in healthcare and save it"
Output: AnalyzedIntent(intent="create_document", topic="AI in healthcare",
                       doc_type="report", output_mode="file", parameters={})
```

---

### 4.5 planner.py — Dynamic Plan Generation

**Purpose:** Convert an `AnalyzedIntent` into an ordered sequence of executable steps.

**How it works:**

1. Queries `tool_server.list_tools()` to discover all available tools and their schemas
2. Queries `agent_registry.list_agents()` to discover all available agents
3. Constructs an LLM prompt containing: the user's intent + available tools + available agents
4. The LLM returns a JSON array of plan steps
5. Each step specifies: which agent, which tool to call, and what parameters

**Class: `PlannerAgent`**

- `generate_plan(intent, context) -> List[PlanStep]`

**Dataclass: `PlanStep`**

```python
@dataclass
class PlanStep:
    step_id: int          # 1-based index
    agent: str            # e.g. "ContentAgent"
    action: str           # e.g. "generate_report" (tool name)
    parameters: dict      # e.g. {"topic": "$context.topic"}
    description: str      # e.g. "Generate the report content"
```

**Key design feature — `$context.*` late binding:**

Parameters can reference context keys with `$context.<key>` syntax. These are NOT resolved at planning time. They are resolved later by the Orchestrator at execution time, after prior steps have populated those context values.

```json
{"topic": "$context.topic"}     // resolved at execution time to "AI in healthcare"
{"text": "$context.text"}       // resolved at execution time to the generated report
```

**Why the planner sees tool schemas:**

The planner receives the full tool catalog (names, descriptions, input schemas) in its prompt. This means:

- It can only plan for tools that actually exist (no hallucinated actions)
- It knows what parameters each tool expects
- Adding new tools automatically makes them available to the planner

---

### 4.6 orchestrator.py — Execution Engine

**Purpose:** Execute the plan step-by-step, routing work to agents and maintaining shared context.

**How it works:**

1. Iterates through plan steps sequentially
2. For each step:
   - Resolves `$context.*` parameter references to actual values
   - Looks up the target agent from the `AgentRegistry`
   - Calls `agent.execute(action, params, context)`
   - Merges the result dict into the shared context
   - Records a trace entry (step_id, status, result_keys)
3. On failure: logs the error, records it in the trace, sets status to "failed", and raises

**Class: `Orchestrator`**

- `execute_plan(plan: List[PlanStep]) -> Context`

**The orchestrator is the ONLY component that:**

- Touches both agents and context
- Acts as the message bus for A2A communication
- Resolves late-bound parameter references
- Tracks execution progress via the trace

---

### 4.7 agents/ — Agent Pool

All agents inherit from `BaseAgent` and share a single contract:

**Abstract Base Class: `BaseAgent`**

```python
class BaseAgent(ABC):
    def __init__(self, tool_server: MCPToolServer)
    @property name -> str                                # unique identifier
    @property capabilities -> List[str]                  # tool names this agent can use
    def execute(action, params, context) -> dict         # delegates to tool server
```

**The rule: Agents are routing shells, not logic containers.**

The `execute` method does exactly two things:

1. Validates that `action` is in the agent's `capabilities` list
2. Calls `self.tool_server.execute_tool(tool_name=action, params=params)`

No business logic lives in an agent. If you find yourself writing `if/else` inside an agent, it should be a tool instead.

#### ContentAgent

| Property         | Value                                                      |
| ---------------- | ---------------------------------------------------------- |
| **Name**         | `ContentAgent`                                             |
| **Capabilities** | `generate_report`, `summarize_text`, `generate_outline`    |
| **Purpose**      | Routes LLM-based content generation tasks to content tools |

#### SystemAgent

| Property         | Value                                                      |
| ---------------- | ---------------------------------------------------------- |
| **Name**         | `SystemAgent`                                              |
| **Capabilities** | `save_file`, `open_file`, `open_application`               |
| **Purpose**      | Routes OS-level file and application tasks to system tools |

#### AgentRegistry

A simple `dict[str, BaseAgent]` lookup. The orchestrator and planner use it to find agents by name.

| Method            | Description                                                       |
| ----------------- | ----------------------------------------------------------------- |
| `register(agent)` | Add an agent to the registry                                      |
| `get(name)`       | Look up an agent by name (raises `AgentNotFoundError` if missing) |
| `list_agents()`   | Return all registered agent names                                 |

---

### 4.8 mcp/ — MCP-Inspired Tool Layer

This is the **critical abstraction layer** that separates what agents want to do from how it gets done.

#### ToolSchema (tool_schema.py)

The public-facing descriptor for a tool. Contains no callable — safe to send to the LLM.

```python
@dataclass
class ToolSchema:
    name: str                    # e.g. "generate_report"
    description: str             # e.g. "Generate a detailed report on a topic"
    input_schema: dict           # e.g. {"topic": {"type": "string", "required": True}}
    output_schema: dict          # e.g. {"text": {"type": "string"}}
```

#### ToolDefinition (tool_schema.py)

The full definition including the callable. Stays inside the tool server.

```python
@dataclass
class ToolDefinition:
    schema: ToolSchema
    function: Callable[..., dict]    # the actual implementation
```

#### ToolRegistry (tool_registry.py)

In-memory storage backend for tool definitions. A simple `dict[str, ToolDefinition]`.

| Method           | Description                                            |
| ---------------- | ------------------------------------------------------ |
| `register(tool)` | Store a tool definition                                |
| `get(name)`      | Look up a tool (raises `ToolNotFoundError` if missing) |
| `list_schemas()` | Return all `ToolSchema` objects (no callables)         |
| `list_all()`     | Return all `ToolDefinition` objects (with callables)   |

#### ToolValidator (tool_validator.py)

Validates parameters against a tool's input schema before execution.

Checks:

- Required fields are present
- Field types match the schema (`string`, `int`, `float`, `bool`, `list`, `dict`)

Returns a list of human-readable error strings (empty list = valid).

#### MCPToolServer (tool_server.py)

The central server that sits between agents and tool implementations.

| Method                       | Description                                              |
| ---------------------------- | -------------------------------------------------------- |
| `register_tool(tool)`        | Register a tool definition                               |
| `list_tools()`               | Discovery: return all tool schemas (used by the Planner) |
| `get_tool_schema(name)`      | Get a single tool's schema                               |
| `execute_tool(name, params)` | Validate → execute → return result                       |

**`execute_tool` pipeline:**

```
1. Look up ToolDefinition from ToolRegistry
2. Validate params against input_schema (ToolValidator)
3. Call tool.function(**params)
4. Normalize result to dict
5. Return result
```

---

### 4.9 tools/ — Tool Implementations

These are the actual functions that do work. Each tool module provides a `register_all()` function that registers its tools with the MCP Tool Server at startup.

#### Content Tools (content_tools.py)

| Tool               | Description                               | Input           | Output            |
| ------------------ | ----------------------------------------- | --------------- | ----------------- |
| `generate_report`  | Generate a full report on a topic via LLM | `topic: string` | `text: string`    |
| `summarize_text`   | Summarize a block of text via LLM         | `text: string`  | `summary: string` |
| `generate_outline` | Generate a structured outline via LLM     | `topic: string` | `outline: string` |

**LLM injection pattern:** Content tools need the LLM client, but tool callables only receive the parameters defined in their input schemas. This is solved with closures at registration time:

```python
# At registration, the llm_client is captured in a closure:
function=lambda topic: generate_report_impl(topic, llm_client)

# At invocation, only 'topic' is passed:
tool_server.execute_tool("generate_report", {"topic": "AI in healthcare"})
```

#### System Tools (system_tools.py)

| Tool               | Description                               | Input                              | Output                 |
| ------------------ | ----------------------------------------- | ---------------------------------- | ---------------------- |
| `save_file`        | Write text content to `output/<filename>` | `text: string`, `filename: string` | `status`, `saved_path` |
| `open_file`        | Open a file in its default application    | `filepath: string`                 | `status`, `filepath`   |
| `open_application` | Launch an application by name             | `app_name: string`                 | `status`, `app`, `pid` |

Files are saved to the `output/` directory relative to the project root.

---

### 4.10 llm/ — LLM Client

**File: `llm/client.py`**

A **provider-agnostic** LLM client built on the OpenAI SDK format. Works with any provider that exposes an OpenAI-compatible chat completions endpoint.

**Class: `LLMClient`**

| Method                                    | Description                                                   |
| ----------------------------------------- | ------------------------------------------------------------- |
| `__init__(api_key, model_name, base_url)` | Create a client for any OpenAI-compatible API                 |
| `generate(prompt)`                        | Send a prompt, return text response                           |
| `generate_json(prompt)`                   | Like `generate` but appends instructions to return valid JSON |

**Supported providers:**

| Provider           | base_url                         | Model Examples            |
| ------------------ | -------------------------------- | ------------------------- |
| **Groq** (default) | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| **OpenAI**         | `https://api.openai.com/v1`      | `gpt-4o-mini`, `gpt-4o`   |
| **Ollama** (local) | `http://localhost:11434/v1`      | `llama3`, `mistral`       |
| **Together AI**    | `https://api.together.xyz/v1`    | `meta-llama/Llama-3-70b`  |

Switching providers requires only changing 3 environment variables in `.env` — zero code changes.

---

### 4.11 utils/logger.py — Logging

Configures a structured logger for the `synapse` namespace. Output format:

```
14:23:01 | INFO     | synapse.orchestrator           | Step 1 completed. Context keys updated: ['text']
```

Controlled by the `LOG_LEVEL` environment variable. Set to `DEBUG` to see LLM prompts and responses.

---

## 5. MCP-Inspired Tool System

### What is MCP?

MCP (Model Context Protocol) is a standard for how AI models interact with external tools. Synapse implements a **lightweight, in-process version** of this pattern.

### MCP Principles Implemented

| MCP Principle                | Synapse Implementation                                                                   |
| ---------------------------- | ---------------------------------------------------------------------------------------- |
| **Tool Abstraction**         | Tools defined via `ToolSchema` with name, description, and typed input/output schemas    |
| **Standardized Interface**   | Every tool follows the identical `ToolDefinition` structure                              |
| **Decoupled Execution**      | Agents never call tool functions directly; `MCPToolServer` mediates all calls            |
| **Dynamic Discovery**        | Planner calls `list_tools()` to see what's available before generating a plan            |
| **Schema-Driven Validation** | `MCPToolServer` validates inputs against `input_schema` before execution                 |
| **Server-Client Separation** | `MCPToolServer` (server) is separate from agents (clients); tools are separate from both |

### Tool Lifecycle

```
1. REGISTRATION  (startup)
   ├── Tool implementations defined in tools/*.py
   ├── register_all() creates ToolDefinition objects (schema + callable)
   └── MCPToolServer.register_tool() stores them in ToolRegistry

2. DISCOVERY  (planning phase)
   ├── Planner calls tool_server.list_tools()
   ├── Gets back List[ToolSchema] (names, descriptions, input schemas — NO callables)
   └── Injects these into the LLM prompt so it can plan valid tool calls

3. INVOCATION  (execution phase)
   ├── Orchestrator dispatches step to Agent
   ├── Agent calls tool_server.execute_tool(tool_name, params)
   ├── MCPToolServer validates params against input_schema
   ├── MCPToolServer calls tool.function(**params)
   └── Result dict returned through Agent → Orchestrator → Context
```

### Agent vs Tool — The Separation

| Concern                  | Agent                      | Tool         |
| ------------------------ | -------------------------- | ------------ |
| Contains business logic  | No                         | Yes          |
| Decides what to do       | No (Planner decides)       | N/A          |
| Calls the tool server    | Yes                        | N/A          |
| Knows which tool to call | Yes (from PlanStep.action) | N/A          |
| Can be added at runtime  | Yes                        | Yes          |
| Registered where         | AgentRegistry              | ToolRegistry |

---

## 6. Execution Flow

### Complete Pipeline — Step by Step

```
STAGE 1: INPUT CAPTURE
══════════════════════
main.py captures raw input from CLI args or interactive prompt.
Context initialized with: { raw_input: "...", status: "initialized" }


STAGE 2: CONTEXT ANALYSIS
═════════════════════════
ContextAnalyzer sends raw input to LLM with extraction prompt.
LLM returns structured JSON.
Parsed into AnalyzedIntent dataclass.

Context updated with:
  + intent: "create_document"
  + topic: "AI in healthcare"
  + doc_type: "report"
  + output_mode: "file"
  + status: "analyzed"


STAGE 3: PLANNING
═════════════════
PlannerAgent:
  1. Queries tool_server.list_tools() → gets all tool schemas
  2. Queries agent_registry.list_agents() → gets ["ContentAgent", "SystemAgent"]
  3. Sends intent + tools + agents to LLM
  4. LLM returns JSON array of plan steps

Context updated with:
  + plan: [
      {step_id: 1, agent: "ContentAgent", action: "generate_report", ...},
      {step_id: 2, agent: "SystemAgent",  action: "save_file", ...},
      {step_id: 3, agent: "SystemAgent",  action: "open_file", ...}
    ]
  + status: "planned"


STAGE 4: EXECUTION
══════════════════
Orchestrator iterates through plan steps:

  Step 1: ContentAgent → generate_report
    ├── Resolve params: {topic: "$context.topic"} → {topic: "AI in healthcare"}
    ├── ContentAgent delegates to tool_server.execute_tool("generate_report", ...)
    ├── Tool calls LLM to generate report text
    └── Context updated: + text: "AI in Healthcare: A Comprehensive Report..."

  Step 2: SystemAgent → save_file
    ├── Resolve params: {text: "$context.text", filename: "report.txt"}
    ├── SystemAgent delegates to tool_server.execute_tool("save_file", ...)
    ├── Tool writes file to output/report.txt
    └── Context updated: + saved_path: "D:\Synapse\output\report.txt"

  Step 3: SystemAgent → open_file
    ├── Resolve params: {filepath: "$context.saved_path"}
    ├── SystemAgent delegates to tool_server.execute_tool("open_file", ...)
    ├── Tool opens file in default application (Notepad)
    └── Context updated: + status: "completed"


STAGE 5: REPORT
═══════════════
main.py prints final status, output path, and execution trace.
Returns context.data dict.
```

---

## 7. A2A Communication Model

### How Agents Communicate

Agents in Synapse **never communicate directly**. There are no imports, method calls, or shared references between agents. All communication is mediated through the **shared Context object**.

```
ContentAgent                    SystemAgent
     │                               │
     │  writes to context:            │
     │  context["text"] = "..."       │
     │──────────────┐                 │
     │              │                 │
     │         ┌────▼─────┐           │
     │         │ CONTEXT   │           │
     │         │           │           │
     │         │ text: "..." ──────────│── reads from context:
     │         │           │           │   context["text"]
     │         └───────────┘           │
     │                                │
```

### Why This Works

- **Loose coupling:** ContentAgent can be replaced without touching SystemAgent
- **Testability:** Mock the context, test any agent in isolation
- **Observability:** The context is a complete record of what happened
- **Scalability:** In production, the Context could be backed by Redis/Kafka for distributed agents

### The Orchestrator as Message Bus

The Orchestrator is the **only component** that touches both agents and context. It:

1. Reads parameters from context (`$context.*` resolution)
2. Passes them to the agent
3. Takes the agent's result
4. Writes it back to context

This makes the Orchestrator the single point of coordination — the "message bus" of the A2A model.

---

## 8. LLM Integration

### Where the LLM is Used

The LLM is called in **three places** in the pipeline:

| Component            | Purpose                                                | Input                               | Output                                         |
| -------------------- | ------------------------------------------------------ | ----------------------------------- | ---------------------------------------------- |
| **Context Analyzer** | Extract structured intent from natural language        | Raw user input                      | JSON with intent, topic, doc_type, output_mode |
| **Planner Agent**    | Generate an execution plan from intent + capabilities  | Intent + tool schemas + agent names | JSON array of plan steps                       |
| **Content Tools**    | Generate actual content (reports, summaries, outlines) | Topic or text                       | Generated content string                       |

### Provider Architecture

```
┌───────────────────────────────────────────┐
│              LLMClient                     │
│  (OpenAI SDK — provider-agnostic)         │
│                                           │
│  api_key ──── from LLM_API_KEY env var    │
│  model   ──── from LLM_MODEL env var      │
│  base_url ─── from LLM_BASE_URL env var   │
└───────────────┬───────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
   ┌────▼────┐   ┌──────▼──────┐
   │  Groq   │   │   OpenAI    │   ... any OpenAI-compatible API
   │  (free) │   │   (paid)    │
   └─────────┘   └─────────────┘
```

Switching providers is a 3-line `.env` change. Zero code modifications.

---

## 9. Directory Structure

```
Synapse/
├── main.py                     # Entry point — wires components, runs pipeline
├── config.py                   # Environment-based configuration
├── context_manager.py          # Shared Context object (A2A bus)
├── context_analyzer.py         # LLM-powered intent extraction
├── planner.py                  # Dynamic plan generation via LLM
├── orchestrator.py             # Step-by-step execution engine
│
├── agents/                     # Agent pool
│   ├── __init__.py
│   ├── base_agent.py           # Abstract base class for all agents
│   ├── agent_registry.py       # Name → agent instance lookup
│   ├── content_agent.py        # LLM content generation routing
│   └── system_agent.py         # OS-level task routing
│
├── mcp/                        # MCP-inspired tool abstraction layer
│   ├── __init__.py
│   ├── tool_schema.py          # ToolSchema + ToolDefinition dataclasses
│   ├── tool_registry.py        # In-memory tool storage
│   ├── tool_server.py          # Central tool execution server
│   └── tool_validator.py       # Schema-based parameter validation
│
├── tools/                      # Concrete tool implementations
│   ├── __init__.py
│   ├── content_tools.py        # generate_report, summarize_text, generate_outline
│   └── system_tools.py         # save_file, open_file, open_application
│
├── llm/                        # LLM client abstraction
│   ├── __init__.py
│   └── client.py               # Provider-agnostic OpenAI SDK client
│
├── utils/                      # Shared utilities
│   ├── __init__.py
│   └── logger.py               # Centralized logging setup
│
├── tests/                      # Test suite
│   └── __init__.py
│
├── output/                     # Generated files are saved here
│
├── System Architectures/       # Original architecture design documents
│   ├── 80% Synapse Architecture (without MCP).md
│   └── mcp.md
│
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not committed)
├── .gitignore                  # Git ignore rules
└── IMPLEMENTATION_PLAN.md      # Detailed implementation plan
```

---

## 10. Configuration & Setup

### Prerequisites

- Python 3.10+
- A free Groq API key (or any OpenAI-compatible provider)

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd Synapse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your API key
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Groq (free, recommended)
LLM_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile
LLM_BASE_URL=https://api.groq.com/openai/v1
LOG_LEVEL=INFO
```

**Alternative provider configurations:**

```env
# OpenAI
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Ollama (fully local, no API key needed)
LLM_API_KEY=ollama
LLM_MODEL=llama3
LLM_BASE_URL=http://localhost:11434/v1
```

### Dependencies

| Package         | Version   | Purpose                                                |
| --------------- | --------- | ------------------------------------------------------ |
| `openai`        | >= 1.0.0  | Provider-agnostic LLM client (OpenAI SDK format)       |
| `pyautogui`     | >= 0.9.54 | OS-level automation (legacy, used by open_application) |
| `python-dotenv` | >= 1.0.0  | Load `.env` files                                      |

### Running

```bash
# Interactive mode
python main.py

# Direct input
python main.py "Create a report on AI in healthcare and save it"
```

---

## 11. Complete Walkthrough Example

**Input:** `"Create a report on AI in healthcare and save it"`

### Stage 1 — Input Capture

```
main.py receives: "Create a report on AI in healthcare and save it"
Context created: { raw_input: "Create a report on AI in healthcare and save it", status: "initialized" }
```

### Stage 2 — Context Analysis

ContextAnalyzer sends this prompt to the LLM:

```
You are an intent extraction engine. Given the user's raw input, extract:
- intent, topic, doc_type, output_mode, parameters

User input: "Create a report on AI in healthcare and save it"
Return ONLY valid JSON.
```

LLM responds:

```json
{
  "intent": "create_document",
  "topic": "AI in healthcare",
  "doc_type": "report",
  "output_mode": "file",
  "parameters": {}
}
```

Context after:

```python
{
    "raw_input": "Create a report on AI in healthcare and save it",
    "intent": "create_document",
    "topic": "AI in healthcare",
    "doc_type": "report",
    "output_mode": "file",
    "status": "analyzed"
}
```

### Stage 3 — Planning

PlannerAgent discovers:

- Available tools: `generate_report`, `summarize_text`, `generate_outline`, `save_file`, `open_file`, `open_application`
- Available agents: `ContentAgent`, `SystemAgent`

Sends intent + tools + agents to LLM. LLM responds:

```json
[
  {
    "step_id": 1,
    "agent": "ContentAgent",
    "action": "generate_report",
    "parameters": { "topic": "$context.topic" },
    "description": "Generate a detailed report on AI in healthcare"
  },
  {
    "step_id": 2,
    "agent": "SystemAgent",
    "action": "save_file",
    "parameters": {
      "text": "$context.text",
      "filename": "AI_in_healthcare_report.txt"
    },
    "description": "Save the generated report to a file"
  },
  {
    "step_id": 3,
    "agent": "SystemAgent",
    "action": "open_file",
    "parameters": { "filepath": "$context.saved_path" },
    "description": "Open the saved report file"
  }
]
```

### Stage 4 — Execution

**Step 1:** Orchestrator resolves `$context.topic` → `"AI in healthcare"`. Dispatches to ContentAgent.

```
ContentAgent → tool_server.execute_tool("generate_report", {"topic": "AI in healthcare"})
  → generate_report_impl calls LLM with "Write a detailed report on 'AI in healthcare'..."
  → returns {"text": "# AI in Healthcare\n\n## Introduction\nArtificial intelligence..."}
```

Context gains: `text = "# AI in Healthcare\n\n## Introduction\n..."` (full report)

**Step 2:** Orchestrator resolves `$context.text` → the generated report. Dispatches to SystemAgent.

```
SystemAgent → tool_server.execute_tool("save_file", {"text": "...", "filename": "AI_in_healthcare_report.txt"})
  → save_file_impl writes to output/AI_in_healthcare_report.txt
  → returns {"status": "file_saved", "saved_path": "D:\Synapse\output\AI_in_healthcare_report.txt"}
```

Context gains: `saved_path = "D:\Synapse\output\AI_in_healthcare_report.txt"`

**Step 3:** Orchestrator resolves `$context.saved_path` → the file path. Dispatches to SystemAgent.

```
SystemAgent → tool_server.execute_tool("open_file", {"filepath": "D:\Synapse\output\AI_in_healthcare_report.txt"})
  → open_file_impl calls os.startfile(filepath)
  → Notepad opens with the report
  → returns {"status": "file_opened", "filepath": "..."}
```

### Stage 5 — Report

```
============================================================
  STATUS : completed
  OUTPUT : D:\Synapse\output\AI_in_healthcare_report.txt
============================================================

Execution trace:
  Step 1: completed
  Step 2: completed
  Step 3: completed
```

### Final Context State

```python
{
    "raw_input": "Create a report on AI in healthcare and save it",
    "intent": "create_document",
    "topic": "AI in healthcare",
    "doc_type": "report",
    "output_mode": "file",
    "plan": [...],
    "text": "# AI in Healthcare\n\n## Introduction\n...",
    "status": "completed",
    "saved_path": "D:\\Synapse\\output\\AI_in_healthcare_report.txt",
}
```

---

## 12. Design Decisions

### Why Non-Hardcoded Architecture?

| Evidence                                                          | Mechanism                                                    |
| ----------------------------------------------------------------- | ------------------------------------------------------------ |
| No `if intent == "create_document"` anywhere                      | The Planner uses an LLM to generate plans dynamically        |
| Adding a new task type requires zero Orchestrator/Planner changes | Just register new tools and agents                           |
| Plan steps are data, not code                                     | `List[PlanStep]` is a runtime-generated sequence             |
| `$context.*` late binding                                         | Parameters are resolved at execution time, not planning time |

A hardcoded system breaks when a new use case appears. Synapse adapts because the LLM planner can compose any sequence of registered tools.

### Why Agents Don't Contain Logic?

If agents contained logic, you'd have two problems:

1. **Duplication** — the same logic might exist in multiple agents
2. **Testing** — you'd need to test agent logic AND tool logic separately

By making agents thin routing shells, all testable logic lives in tools. Agents are just capability declarations + delegation.

### Why a Shared Context Instead of Direct Communication?

Direct agent communication creates tight coupling:

```
ContentAgent.generate() → result → SystemAgent.save(result)  // coupled
```

Context-mediated communication keeps agents independent:

```
ContentAgent writes context["text"]
SystemAgent reads context["text"]     // no coupling
```

### Why Provider-Agnostic LLM Client?

The original implementation was locked to Google Gemini. When Gemini's free tier was exhausted, the system was unusable. By switching to the OpenAI SDK format (which Groq, OpenAI, Ollama, and others all support), Synapse can switch providers with a 3-line `.env` change — no code modifications.

### Why Direct File I/O Instead of pyautogui?

The original system tools used `pyautogui.write()` to type text into Notepad. This was unreliable because:

- It types into whatever window happens to be focused
- It can't handle special characters or newlines properly
- It races with window focus timing

The current implementation writes files directly with Python file I/O (`Path.write_text()`), then optionally opens the result in the default application. Deterministic, reliable, fast.

---

## 13. Extending the System

### Adding a New Tool

1. Create the implementation function in `tools/`:

```python
def search_web_impl(query: str) -> dict:
    # ... implementation ...
    return {"results": [...]}
```

2. Register it in the module's `register_all()`:

```python
tool_server.register_tool(ToolDefinition(
    schema=ToolSchema(
        name="search_web",
        description="Search the web for a query",
        input_schema={"query": {"type": "string", "required": True}},
        output_schema={"results": {"type": "array"}},
    ),
    function=search_web_impl,
))
```

3. The Planner automatically discovers it via `list_tools()`. No other changes needed.

### Adding a New Agent

1. Create a new file in `agents/`:

```python
class WebAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "WebAgent"

    @property
    def capabilities(self) -> List[str]:
        return ["search_web", "scrape_page"]
```

2. Register it in `main.py`:

```python
agent_registry.register(WebAgent(tool_server))
```

3. The Planner automatically discovers it via `list_agents()`.

### Adding a New LLM Provider

Just change the `.env`:

```env
LLM_API_KEY=new_provider_key
LLM_MODEL=new_model_name
LLM_BASE_URL=https://new-provider.com/v1
```

No code changes required — as long as the provider supports the OpenAI chat completions format.

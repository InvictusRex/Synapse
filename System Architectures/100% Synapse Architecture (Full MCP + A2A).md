## User Input Layer:
- Raw input is captured using CLI / UI / Voice interface  
- Acts as the entry point into the system  
```python
context = {
    "raw_input": "Create a report on AI in healthcare and save it"
}
```
## Interaction Agent:
- Handles natural language understanding  
- Cleans and structures user input  
- Handles ambiguity and clarification (if needed)  
- Converts raw input → structured intent  
-  Output:
```json
{
  "intent": "create_document",
  "document_type": "report",
  "topic": "AI in healthcare",
  "output_mode": "file"
}
```
## Context Manager:
- Centralized state manager (core of system)  
- Stores:
	  - User input  
	  - Parsed intent  
	  - Task graph  
	  - Intermediate results  
	  - Execution state  
```python
context = {
    "session_id": "123",
    "raw_input": "...",
    "intent": "...",
    "entities": {},
    "task_graph": {},
    "results": {},
    "memory_logs": []
}
```
## Planner Agent:
- Core intelligence layer (LLM-powered)  
- Converts structured intent → execution strategy  
- Performs:
	  - Task decomposition  
	  - Tool selection  
	  - Dependency mapping  
- Output: Task Graph (DAG)
```json
{
  "tasks": [
    {
      "id": "T1",
      "tool": "generate_report",
      "args": {"topic": "AI in healthcare"},
      "deps": []
    },
    {
      "id": "T2",
      "tool": "open_notepad",
      "deps": []
    },
    {
      "id": "T3",
      "tool": "type_text",
      "deps": ["T1", "T2"]
    },
    {
      "id": "T4",
      "tool": "save_file",
      "deps": ["T3"]
    }
  ]
}
```
- Context Update:
```python
context["task_graph"] = task_graph
```
## Task Graph Engine (DAG Manager):
- Stores and validates task dependencies  
- Enables:
	  - Sequential execution  
	  - Parallel execution (if applicable)  
- Ensures correct order of execution  
## Orchestrator (Graph Executor):
- Executes the DAG dynamically  
- Resolves dependencies  
- Dispatches tasks  
- Handles retries and failures  
### Core Execution Loop:

```python
while not all_tasks_done:
    ready_tasks = get_ready_tasks(task_graph)
    for task in ready_tasks:
        dispatch(task)
```

## A2A Communication Layer (Agent-to-Agent Bus):
### Purpose:
- Enables communication between agents  
- Decouples system components  
- Allows asynchronous coordination  
### Message Format:
```python
message = {
    "from": "PlannerAgent",
    "to": "ContentAgent",
    "type": "task_request",
    "payload": {...}
}
```
### Implementation:
- Python Queue (MVP)
- Redis Pub/Sub (advanced)
### Behavior:
- Agents DO NOT call each other directly  
- All communication happens via message bus or shared context  

## MCP Server (Model Context Protocol Layer):
### Core Component — Tool Abstraction Layer
### Responsibilities:
- Tool registration  
- Tool schema validation  
- Tool execution routing  
- Standardized interface between agents and tools  
### Tool Schema Example:
```json
{
  "name": "generate_report",
  "description": "Generate a report on a given topic",
  "parameters": {
    "type": "object",
    "properties": {
      "topic": {
        "type": "string"
      }
    },
    "required": ["topic"]
  }
}
```
### Tool Registry:
```python
tool_registry = {
    "generate_report": MCPTool(generate_report),
    "open_notepad": MCPTool(open_notepad),
    "type_text": MCPTool(type_text),
    "save_file": MCPTool(save_file)
}
```
### Tool Invocation Format (MCP Style):
```json
{
  "tool": "generate_report",
  "arguments": {
    "topic": "AI in healthcare"
  }
}
```
### Execution Flow:
```python
tool = tool_registry[tool_name]
result = tool.execute(args)
```
## Agent Pool (Worker Agents):
### 1. Content Agent:
- Handles LLM-based generation  
```python
def execute(task, context):
    topic = context["entities"]["topic"]
    text = generate_report(topic)
    return {"text": text}
```
### 2. System Agent:
- Handles OS-level automation  
```python
subprocess.Popen(['notepad.exe'])
pyautogui.write(context["text"])
```
### 3. File Agent:
- Handles file operations  
```python
pyautogui.hotkey('ctrl', 's')
pyautogui.write("report.txt")
pyautogui.press('enter')
```
## Tool Adapters:
- Wrap external systems into MCP-compatible tools  

## Memory Engine:
### Working Memory:
- Stores current execution state  
### Execution Memory:
- Tracks tool usage and execution  
```python
memory_logs.append({
    "task_id": "T1",
    "tool": "generate_report",
    "status": "success"
})
```
### Semantic Memory (Optional):
- Stores embeddings for recall  

## Full Execution Flow:
1. User Input → Interaction Agent  
2. Context Manager stores structured intent  
3. Planner Agent generates DAG  
4. Orchestrator executes tasks  
5. Tasks dispatched via A2A Bus  
6. Agents call MCP Server  
7. Tools executed  
8. Memory updated  
9. Context updated  
10. Next tasks executed  
## Final Summary:
Synapse is a distributed multi-agent system implementing A2A communication through a message bus and MCP-compliant tool abstraction. It dynamically decomposes tasks into a DAG, executes them via an orchestrator, and maintains execution state through a layered memory engine.
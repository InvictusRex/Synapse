## User Input Layer:
- raw input is captured using CLI or UI
- original context:

```python
context = {
    "raw_input": "Create a report on AI in healthcare and save it"
}
```
## Context Analyzer:
- understands the intent
- normalizes the input into structured data
- parses the user input
- extracts key tasks
- identifies task type, topic and output requirement
- output as:
```json
{
  "intent": "create_document",
  "document_type": "report",
  "topic": "AI in healthcare",
  "output_mode": "file"
}
```
- updates the context like:
```python
context.update({
    "intent": "create_document",
    "topic": "AI in healthcare",
    "doc_type": "report"
})
```
## Planner Agent:
- converts structured data and intent into executable plan
- this is the core intelligence layer
- looks at intent & available agents and then decides sequence of actions & which agent handles what tasks
- output as:
```json
[
  {"agent": "ContentAgent", "action": "generate_report"},
  {"agent": "SystemAgent", "action": "open_notepad"},
  {"agent": "SystemAgent", "action": "type_text"},
  {"agent": "SystemAgent", "action": "save_file"}
]
```
- context updated as:
```python
context["plan"] = plan
```
- this proves no hardcoded dynamic workflow generation

## Orchestrator:
- This is the execution engine
- It executes the plan step by step
- Routes tasks to correct agents
- Maintains shared state
- Core idea for the orchestrator:
```python
for step in context["plan"]:
    agent = agent_registry[step["agent"]]
    result = agent.execute(step, context)
    context.update(result)
```
- No agent can talk to each other directly and all communication is via context
- This simulates A2A communication

## Agent Pool:
#### 1. Content Agent:
- Generates the report using Gemini API or any other LLM
- Input from Context:
```python
context["topic"] = "AI in healthcare"
```
- Action performed:
```python
generate_report("AI in healthcare")
```
- Output given:
```python
return {
    "text": "AI in healthcare is transforming diagnostics..."
}
```
- Context Update:
```python
context["text"] = generated_text
```

#### 2. System Agent:
- Handles OS level executions like opening apps and actually writing the content in them.
- Uses tools like pyautogui
- Opens Notepad:
```python
subprocess.Popen(['notepad.exe'])
```
- Types in the actual text:
```python
pyautogui.write(context["text"])
```
- Saves the file in the system:
```python
pyautogui.hotkey('ctrl', 's')
pyautogui.write("report.txt")
pyautogui.press('enter')
```
- Maybe can have different agents for writing the file content and saving the file, depends on how much modularity is needed.

## Architecture Concepts to Implement:
1. Shared Context: Agents communicate through a centralized context object
2. Dynamic Planning: The planner generates execution steps at runtime
3. Agent Abstraction: Each agent encapsulates a specific capability
4. Loose Coupling: Agents are decoupled and orchestrated centrally
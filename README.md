# Synapse - Multi-Agent System with MCP + A2A

A proof-of-concept multi-agent system implementing A2A (Agent-to-Agent) communication and MCP (Model Context Protocol) style tool abstraction.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key (use Groq - it's free and fast)
$env:GROQ_API_KEY="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"

# Run the demo
streamlit run app.py
```

## Architecture

- **Planner Agent**: LLM-powered task decomposition into DAG
- **Orchestrator**: Executes tasks respecting dependencies
- **A2A Bus**: Message queue for agent communication
- **MCP Server**: Tool registry with schema validation
- **Tools**: Web search, file operations, text generation, etc.

## Demo Use Cases

1. "Research AI in healthcare and write a summary report"
2. "Search for latest news on climate change and create bullet points"
3. "Analyze the topic 'renewable energy' and save findings to a file"

## Project Structure

```
synapse/
├── app.py              # Streamlit UI
├── core/
│   ├── context.py      # Context Manager
│   ├── planner.py      # LLM Planner Agent
│   ├── orchestrator.py # DAG Executor
│   └── a2a_bus.py      # Agent-to-Agent Message Bus
├── mcp/
│   ├── server.py       # MCP Server
│   ├── registry.py     # Tool Registry
│   └── tools/          # Tool implementations
│       ├── web_search.py
│       ├── file_ops.py
│       └── text_gen.py
└── config.py           # Configuration
```

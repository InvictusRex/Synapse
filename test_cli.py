#!/usr/bin/env python3
"""
CLI Test Script for Synapse
Run this to test the system without Streamlit
"""
import os
import sys

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.context import ContextManager
from core.planner import PlannerAgent
from core.orchestrator import Orchestrator
from mcp.tool_loader import register_all_tools

def main():
    print("=" * 60)
    print("🧠 SYNAPSE - Multi-Agent System Test")
    print("=" * 60)
    
    # Check API key
    if not os.environ.get("GROQ_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        print("\n❌ Error: No API key set")
        print("Run one of:")
        print("  export GEMINI_API_KEY='your-key-here'  (recommended)")
        print("  export GROQ_API_KEY='your-key-here'")
        print("\nGet free keys at:")
        print("  Gemini: https://aistudio.google.com/apikey")
        print("  Groq: https://console.groq.com")
        return
    
    provider = "Gemini" if os.environ.get("GEMINI_API_KEY") else "Groq"
    print(f"Using LLM provider: {provider}")
    
    # Initialize
    print("\n📦 Initializing system...")
    register_all_tools()
    
    context_manager = ContextManager()
    planner = PlannerAgent()
    orchestrator = Orchestrator()
    
    # Test query
    test_queries = [
        "Search for latest AI news and summarize it",
        "Generate a short report on renewable energy",
    ]
    
    query = test_queries[0]
    print(f"\n📝 Test Query: {query}")
    print("-" * 40)
    
    # Create context
    context = context_manager.create_context(query)
    print(f"Session: {context.session_id}")
    
    # Plan
    print("\n🤔 Planning...")
    try:
        tasks = planner.plan(context)
        context.task_graph = tasks
        
        print(f"Generated {len(tasks)} tasks:")
        for task in tasks:
            print(f"  - {task.id}: {task.tool} (deps: {task.deps})")
    except Exception as e:
        print(f"❌ Planning failed: {e}")
        return
    
    # Execute
    print("\n⚡ Executing...")
    success = orchestrator.execute(context)
    
    # Results
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    for task in context.task_graph:
        status_icon = "✅" if task.status == "success" else "❌"
        print(f"\n{status_icon} {task.id}: {task.tool}")
        print(f"   Status: {task.status}")
        if task.result:
            result_str = str(task.result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            print(f"   Result: {result_str}")
        if task.error:
            print(f"   Error: {task.error}")
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tasks completed successfully!")
    else:
        print("⚠️ Some tasks failed")
    print("=" * 60)

if __name__ == "__main__":
    main()

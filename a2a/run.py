"""
A2A Server Entry Point
Wires up Synapse + A2A protocol server and runs uvicorn
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)


def main():
    """Start the A2A protocol server"""
    import uvicorn
    from synapse import Synapse
    from a2a.streaming import StreamManager
    from a2a.push_notifications import PushNotificationDispatcher
    from a2a.task_manager import TaskManager
    from a2a.agent_registry import AgentRegistry
    from a2a.server import create_app

    # Initialize Synapse
    print("Initializing Synapse multi-agent system...")
    synapse = Synapse()

    # Initialize A2A components
    stream_manager = StreamManager()
    push_dispatcher = PushNotificationDispatcher()
    task_manager = TaskManager(
        stream_manager=stream_manager,
        push_dispatcher=push_dispatcher,
    )
    agent_registry = AgentRegistry(synapse, task_manager)

    # Create FastAPI app
    app = create_app(
        synapse=synapse,
        task_manager=task_manager,
        agent_registry=agent_registry,
        stream_manager=stream_manager,
        push_dispatcher=push_dispatcher,
    )

    # Run server
    host = os.environ.get("A2A_HOST", "0.0.0.0")
    port = int(os.environ.get("A2A_PORT", "8000"))

    print(f"\nStarting A2A Protocol Server on {host}:{port}")
    print(f"Agent Card: http://localhost:{port}/.well-known/agent.json")
    print(f"Health:     http://localhost:{port}/health")
    print(f"API Docs:   http://localhost:{port}/docs\n")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

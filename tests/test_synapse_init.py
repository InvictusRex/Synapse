"""
Tests for Synapse system initialization with new agents
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from tools.all_tools import register_all_tools


@pytest.fixture
def synapse():
    """Create a Synapse instance"""
    from synapse import Synapse
    s = Synapse()
    yield s
    s.shutdown()


class TestSynapseAgentInitialization:

    def test_codegen_agent_exists(self, synapse):
        assert hasattr(synapse, "codegen_agent")
        assert synapse.codegen_agent is not None

    def test_scaffolding_agent_exists(self, synapse):
        assert hasattr(synapse, "scaffolding_agent")
        assert synapse.scaffolding_agent is not None

    def test_implementation_agent_exists(self, synapse):
        assert hasattr(synapse, "implementation_agent")
        assert synapse.implementation_agent is not None

    def test_all_agents_count(self, synapse):
        agents = synapse.get_all_agents()
        assert len(agents) == 10  # 3 meta + 4 original workers + 3 new workers

    def test_new_agents_running(self, synapse):
        assert synapse.codegen_agent.running is True
        assert synapse.scaffolding_agent.running is True
        assert synapse.implementation_agent.running is True


class TestSynapseOrchestratorRegistration:

    def test_codegen_registered_with_orchestrator(self, synapse):
        assert "codegen_agent" in synapse.orchestrator.worker_agents
        assert synapse.orchestrator.worker_agents["codegen_agent"] is synapse.codegen_agent

    def test_scaffolding_registered_with_orchestrator(self, synapse):
        assert "scaffolding_agent" in synapse.orchestrator.worker_agents
        assert synapse.orchestrator.worker_agents["scaffolding_agent"] is synapse.scaffolding_agent

    def test_implementation_registered_with_orchestrator(self, synapse):
        assert "implementation_agent" in synapse.orchestrator.worker_agents
        assert synapse.orchestrator.worker_agents["implementation_agent"] is synapse.implementation_agent

    def test_total_worker_agents(self, synapse):
        assert len(synapse.orchestrator.worker_agents) == 7  # 4 original + 3 new


class TestSynapseBusRegistration:

    def test_all_agents_on_bus(self, synapse):
        registered = synapse.bus.get_registered_agents()
        assert "codegen_agent" in registered
        assert "scaffolding_agent" in registered
        assert "implementation_agent" in registered

    def test_total_bus_agents(self, synapse):
        registered = synapse.bus.get_registered_agents()
        assert len(registered) == 10


class TestSynapseMCPIntegration:

    def test_dev_tools_registered(self, synapse):
        from mcp.server import ToolCategory
        dev_tools = synapse.mcp.get_tools_by_category(ToolCategory.DEVELOPMENT)
        assert len(dev_tools) == 5

    def test_total_tools(self, synapse):
        assert len(synapse.mcp.tools) == 28


class TestSynapseStatus:

    def test_status_includes_new_agents(self, synapse):
        status = synapse.get_status()
        agent_names = [a["name"] for a in status["agents"]]
        assert "CodeGen Agent" in agent_names
        assert "Scaffolding Agent" in agent_names
        assert "Implementation Agent" in agent_names

    def test_status_new_agents_running(self, synapse):
        status = synapse.get_status()
        for agent in status["agents"]:
            if agent["name"] in ["CodeGen Agent", "Scaffolding Agent", "Implementation Agent"]:
                assert agent["running"] is True

    def test_status_new_agents_have_tools(self, synapse):
        status = synapse.get_status()
        for agent in status["agents"]:
            if agent["name"] == "CodeGen Agent":
                assert len(agent["tools"]) > 0
                assert "generate_template" in agent["tools"]
            elif agent["name"] == "Scaffolding Agent":
                assert len(agent["tools"]) > 0
                assert "scaffold_project" in agent["tools"]
            elif agent["name"] == "Implementation Agent":
                assert len(agent["tools"]) > 0
                assert "implement_section" in agent["tools"]

    def test_status_mcp_tool_count(self, synapse):
        status = synapse.get_status()
        assert status["mcp"]["tools_registered"] == 28

    def test_status_bus_agent_count(self, synapse):
        status = synapse.get_status()
        assert len(status["bus"]["registered_agents"]) == 10


class TestSynapseShutdown:

    def test_shutdown_stops_new_agents(self, synapse):
        synapse.shutdown()
        assert synapse.codegen_agent.running is False
        assert synapse.scaffolding_agent.running is False
        assert synapse.implementation_agent.running is False

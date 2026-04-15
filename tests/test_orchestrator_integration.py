"""
Tests for Orchestrator integration with new software agents
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from tools.all_tools import register_all_tools
from agents.orchestrator_agent import OrchestratorAgent
from agents.codegen_agent import CodeGenAgent
from agents.scaffolding_agent import ScaffoldingAgent
from agents.implementation_agent import ImplementationAgent


@pytest.fixture
def orchestrator_with_agents():
    """Create orchestrator with all new agents registered"""
    register_all_tools()

    orchestrator = OrchestratorAgent()
    codegen = CodeGenAgent()
    scaffolding = ScaffoldingAgent()
    implementation = ImplementationAgent()

    orchestrator.register_worker_agent("codegen_agent", codegen)
    orchestrator.register_worker_agent("scaffolding_agent", scaffolding)
    orchestrator.register_worker_agent("implementation_agent", implementation)

    orchestrator.start()
    codegen.start()
    scaffolding.start()
    implementation.start()

    yield orchestrator, codegen, scaffolding, implementation

    orchestrator.stop()
    codegen.stop()
    scaffolding.stop()
    implementation.stop()


class TestOrchestratorWorkerRegistration:

    def test_codegen_agent_registered(self, orchestrator_with_agents):
        orch, *_ = orchestrator_with_agents
        assert "codegen_agent" in orch.worker_agents

    def test_scaffolding_agent_registered(self, orchestrator_with_agents):
        orch, *_ = orchestrator_with_agents
        assert "scaffolding_agent" in orch.worker_agents

    def test_implementation_agent_registered(self, orchestrator_with_agents):
        orch, *_ = orchestrator_with_agents
        assert "implementation_agent" in orch.worker_agents

    def test_worker_agent_instances(self, orchestrator_with_agents):
        orch, codegen, scaffolding, implementation = orchestrator_with_agents
        assert orch.worker_agents["codegen_agent"] is codegen
        assert orch.worker_agents["scaffolding_agent"] is scaffolding
        assert orch.worker_agents["implementation_agent"] is implementation


class TestOrchestratorExecutePlanWithCodeGen:

    def test_execute_plan_generate_template(self, orchestrator_with_agents):
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "test_codegen",
            "description": "Generate a Python class",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "codegen_agent",
                    "tool": "generate_template",
                    "args": {
                        "template_type": "python:class",
                        "name": "OrderService",
                        "description": "Manages orders"
                    },
                    "depends_on": []
                }
            ]
        }
        result = orch.execute_plan(plan)
        assert result["success"] is True
        assert result["tasks_completed"] == 1
        assert result["tasks_failed"] == 0

    def test_execute_plan_list_templates(self, orchestrator_with_agents):
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "test_list",
            "description": "List templates",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "codegen_agent",
                    "tool": "list_templates",
                    "args": {},
                    "depends_on": []
                }
            ]
        }
        result = orch.execute_plan(plan)
        assert result["success"] is True
        assert result["tasks_completed"] == 1


class TestOrchestratorExecutePlanWithScaffolding:

    def test_execute_plan_scaffold_project(self, orchestrator_with_agents, temp_dir):
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "test_scaffold",
            "description": "Scaffold a project",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "scaffolding_agent",
                    "tool": "scaffold_project",
                    "args": {
                        "project_name": "OrchestratedApp",
                        "template": "python",
                        "directory": temp_dir
                    },
                    "depends_on": []
                }
            ]
        }
        result = orch.execute_plan(plan)
        assert result["success"] is True
        assert result["tasks_completed"] == 1
        assert os.path.isdir(os.path.join(temp_dir, "OrchestratedApp"))
        assert os.path.isfile(os.path.join(temp_dir, "OrchestratedApp", "main.py"))


class TestOrchestratorExecutePlanWithImplementation:

    def test_execute_plan_implement_backend(self, orchestrator_with_agents, temp_dir):
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "test_impl",
            "description": "Implement backend",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "implementation_agent",
                    "tool": "implement_section",
                    "args": {
                        "section": "backend",
                        "tech": "python",
                        "project_name": "TestApp",
                        "directory": temp_dir
                    },
                    "depends_on": []
                }
            ]
        }
        result = orch.execute_plan(plan)
        assert result["success"] is True
        assert result["tasks_completed"] == 1
        assert os.path.isdir(os.path.join(temp_dir, "backend"))


class TestOrchestratorMultiAgentPlan:

    def test_multi_task_plan_with_new_agents(self, orchestrator_with_agents, temp_dir):
        """Test a plan that uses multiple new agents in sequence"""
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "multi_agent_test",
            "description": "Scaffold project and implement sections",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "codegen_agent",
                    "tool": "list_templates",
                    "args": {},
                    "depends_on": []
                },
                {
                    "task_id": "T2",
                    "agent": "scaffolding_agent",
                    "tool": "scaffold_project",
                    "args": {
                        "project_name": "FullApp",
                        "template": "python",
                        "directory": temp_dir
                    },
                    "depends_on": []
                },
                {
                    "task_id": "T3",
                    "agent": "implementation_agent",
                    "tool": "implement_section",
                    "args": {
                        "section": "testing",
                        "tech": "python",
                        "project_name": "FullApp",
                        "directory": os.path.join(temp_dir, "FullApp")
                    },
                    "depends_on": ["T2"]
                }
            ]
        }
        result = orch.execute_plan(plan)
        assert result["success"] is True
        assert result["tasks_completed"] == 3
        assert result["tasks_failed"] == 0
        # Verify files from scaffold
        assert os.path.isfile(os.path.join(temp_dir, "FullApp", "main.py"))
        # Verify files from implementation
        assert os.path.isdir(os.path.join(temp_dir, "FullApp", "testing"))

    def test_plan_with_unknown_agent_fails_gracefully(self, orchestrator_with_agents):
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "bad_agent",
            "description": "Plan with unknown agent",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "nonexistent_agent",
                    "tool": "some_tool",
                    "args": {},
                    "depends_on": []
                }
            ]
        }
        result = orch.execute_plan(plan)
        assert result["tasks_failed"] == 1
        assert result["tasks_completed"] == 0


class TestOrchestratorResultAggregation:

    def test_aggregate_scaffold_result(self, orchestrator_with_agents, temp_dir):
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "agg_test",
            "description": "Scaffold and check aggregation",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "scaffolding_agent",
                    "tool": "scaffold_project",
                    "args": {
                        "project_name": "AggApp",
                        "template": "node",
                        "directory": temp_dir
                    },
                    "depends_on": []
                }
            ]
        }
        result = orch.execute_plan(plan)
        final = result["final_result"]
        assert "all_outputs" in final
        assert len(final["all_outputs"]) == 1
        output = final["all_outputs"][0]
        assert output["type"] == "scaffold_project"
        assert "project_name" in output["content"]

    def test_aggregate_generate_template_result(self, orchestrator_with_agents):
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "agg_template",
            "description": "Generate template and check aggregation",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "codegen_agent",
                    "tool": "generate_template",
                    "args": {
                        "template_type": "python:function",
                        "name": "helper"
                    },
                    "depends_on": []
                }
            ]
        }
        result = orch.execute_plan(plan)
        final = result["final_result"]
        output = final["all_outputs"][0]
        assert output["type"] == "generate_template"
        assert "code" in output["content"]

    def test_aggregate_implement_section_result(self, orchestrator_with_agents, temp_dir):
        orch, *_ = orchestrator_with_agents
        plan = {
            "plan_id": "agg_impl",
            "description": "Implement section and check aggregation",
            "tasks": [
                {
                    "task_id": "T1",
                    "agent": "implementation_agent",
                    "tool": "implement_section",
                    "args": {
                        "section": "database",
                        "tech": "sql",
                        "project_name": "TestApp",
                        "directory": temp_dir
                    },
                    "depends_on": []
                }
            ]
        }
        result = orch.execute_plan(plan)
        final = result["final_result"]
        output = final["all_outputs"][0]
        assert output["type"] == "implement_section"
        assert "section" in output["content"]
        assert "files_created" in output["content"]

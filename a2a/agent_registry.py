"""
A2A Agent Registry
Maps Synapse internal agents to A2A protocol skills and builds the AgentCard
"""
import os
import base64
import json
from typing import Any, Optional

from a2a.models import (
    A2AMessage,
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    Artifact,
    ArtifactType,
    AuthScheme,
    MessageRole,
    SkillInputSchema,
    TaskStatus,
)
from a2a.task_manager import TaskManager


# Skill definitions derived from Synapse agent capabilities
SKILL_DEFINITIONS = [
    AgentSkill(
        id="general",
        name="General Task Execution",
        description="Execute any task through the multi-agent pipeline. Automatically plans, decomposes, and executes complex requests using all available agents.",
        input_schema=SkillInputSchema(
            properties={"message": {"type": "string", "description": "Natural language task description"}},
            required=["message"],
        ),
        example_prompts=[
            "List files on my Desktop",
            "Write an article about AI and save it as article.txt",
            "What time is it?",
        ],
    ),
    AgentSkill(
        id="file_operations",
        name="File Operations",
        description="Read, write, copy, move, delete files and manage directories.",
        input_schema=SkillInputSchema(
            properties={"message": {"type": "string", "description": "File operation to perform"}},
            required=["message"],
        ),
        example_prompts=[
            "Create a file called notes.txt with content 'Hello World'",
            "List all files in the current directory",
            "Move report.txt to the Documents folder",
        ],
    ),
    AgentSkill(
        id="content_generation",
        name="Content Generation",
        description="Generate articles, reports, summaries, and other text content using AI.",
        input_schema=SkillInputSchema(
            properties={"message": {"type": "string", "description": "Content to generate"}},
            required=["message"],
        ),
        example_prompts=[
            "Write an article about machine learning",
            "Summarize this text: ...",
        ],
    ),
    AgentSkill(
        id="code_generation",
        name="Code Generation",
        description="Generate code from templates or AI prompts. Supports Python, JavaScript, HTML templates for classes, functions, routes, components.",
        input_schema=SkillInputSchema(
            properties={"message": {"type": "string", "description": "Code to generate"}},
            required=["message"],
        ),
        example_prompts=[
            "Generate a Python class called UserService",
            "Create a FastAPI router for handling products",
            "List all available code templates",
        ],
    ),
    AgentSkill(
        id="project_scaffolding",
        name="Project Scaffolding",
        description="Bootstrap new projects with complete directory structures. Supports Python, Node.js, React, Flask, FastAPI, Express, HTML stacks.",
        input_schema=SkillInputSchema(
            properties={"message": {"type": "string", "description": "Project to scaffold"}},
            required=["message"],
        ),
        example_prompts=[
            "Scaffold a new React project called my-app",
            "Create a Python Flask project called api-server",
        ],
    ),
    AgentSkill(
        id="section_implementation",
        name="Section Implementation",
        description="Implement complete project sections: backend (Flask/Express), frontend (React/HTML), database (SQL), API (REST), testing (unittest/Jest).",
        input_schema=SkillInputSchema(
            properties={"message": {"type": "string", "description": "Section to implement"}},
            required=["message"],
        ),
        example_prompts=[
            "Implement a Python backend for my-project",
            "Implement a React frontend for my-project",
            "Implement a SQL database schema for my-project",
        ],
    ),
    AgentSkill(
        id="web_operations",
        name="Web Operations",
        description="Fetch webpages, download files from URLs.",
        input_schema=SkillInputSchema(
            properties={"message": {"type": "string", "description": "Web operation to perform"}},
            required=["message"],
        ),
        example_prompts=[
            "Fetch the content of https://example.com",
            "Download a file from a URL",
        ],
    ),
    AgentSkill(
        id="system_operations",
        name="System Operations",
        description="Run shell commands, get system info, calculate math expressions, get current date/time.",
        input_schema=SkillInputSchema(
            properties={"message": {"type": "string", "description": "System operation to perform"}},
            required=["message"],
        ),
        example_prompts=[
            "What is the current directory?",
            "Get system information",
            "Calculate 256 * 4 + sqrt(144)",
        ],
    ),
]


class AgentRegistry:
    """
    Maps Synapse agents to A2A protocol skills.
    Builds the AgentCard and executes tasks via Synapse pipeline.
    """

    def __init__(self, synapse, task_manager: TaskManager):
        self.synapse = synapse
        self.task_manager = task_manager
        self.skills = {skill.id: skill for skill in SKILL_DEFINITIONS}

    def get_agent_card(self, base_url: str) -> AgentCard:
        """Build the agent card for discovery"""
        return AgentCard(
            name="Synapse",
            description="Multi-Agent System with A2A Communication & MCP Tools. "
                        "Synapse orchestrates specialized agents for file operations, "
                        "content generation, code generation, project scaffolding, "
                        "web operations, and system tasks.",
            url=base_url,
            version="1.0.0",
            capabilities=AgentCapabilities(
                streaming=True,
                push_notifications=True,
                state_transition_history=True,
            ),
            skills=list(self.skills.values()),
            auth_schemes=[
                AuthScheme(
                    scheme="apiKey",
                    description="API key via x-api-key header",
                    config={"header": "x-api-key"},
                ),
                AuthScheme(
                    scheme="bearer",
                    description="Bearer token via Authorization header",
                    config={"header": "Authorization", "prefix": "Bearer"},
                ),
            ],
        )

    def execute(self, task_id: str, user_message: str,
                skill_id: Optional[str] = None,
                working_dir: Optional[str] = None) -> None:
        """
        Execute a task through the Synapse pipeline.
        Called from a thread (via asyncio.to_thread).
        Updates task state and streams real-time progress via SSE.
        """
        wd = working_dir or os.getcwd()

        # Transition to working
        self.task_manager.transition(task_id, TaskStatus.WORKING, "Processing started")

        # Build progress callback that emits SSE events during execution
        def progress_callback(event_type: str, data: dict):
            self.task_manager.emit_progress(task_id, event_type, data)

        try:
            result = self.synapse.process(user_message, wd, progress_callback=progress_callback)

            # Extract artifacts from execution result
            self._extract_artifacts(task_id, result)

            # Add agent response message
            formatted = result.get("formatted_result", "")
            if not formatted:
                final = result.get("final_output", {})
                outputs = final.get("all_outputs", [])
                if outputs:
                    parts = []
                    for out in outputs:
                        content = out.get("content", "")
                        if isinstance(content, dict):
                            parts.append(json.dumps(content, indent=2))
                        elif content:
                            parts.append(str(content))
                    formatted = "\n\n".join(parts) if parts else "Task completed."
                else:
                    formatted = "Task completed."

            self.task_manager.add_message(
                task_id,
                A2AMessage(role=MessageRole.AGENT, content=str(formatted)),
            )

            if result.get("success"):
                self.task_manager.transition(task_id, TaskStatus.COMPLETED, "Task completed successfully")
            else:
                error_msg = result.get("error", "Task failed")
                self.task_manager.transition(task_id, TaskStatus.FAILED, str(error_msg))

        except Exception as e:
            # Add error message
            self.task_manager.add_message(
                task_id,
                A2AMessage(role=MessageRole.AGENT, content=f"Error: {str(e)}"),
            )
            self.task_manager.transition(task_id, TaskStatus.FAILED, str(e))

    def _extract_artifacts(self, task_id: str, result: dict) -> None:
        """Extract artifacts from Synapse execution result"""
        final = result.get("final_output", {})
        outputs = final.get("all_outputs", [])

        for output in outputs:
            tool_type = output.get("type", "")
            content = output.get("content", "")

            if tool_type in ("write_file", "create_file") and isinstance(content, dict):
                filepath = content.get("filepath", "")
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.FILE,
                    name=os.path.basename(filepath) if filepath else "file",
                    mime_type="application/octet-stream",
                    description=f"Created file: {filepath}",
                    uri=filepath,
                ))

            elif tool_type == "generate_text" and isinstance(content, str):
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.TEXT,
                    name="generated_content",
                    mime_type="text/plain",
                    description="AI-generated text content",
                    data=content[:10000],
                ))

            elif tool_type == "generate_template" and isinstance(content, dict):
                code = content.get("code", "")
                lang = content.get("language", "text")
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.TEXT,
                    name=f"template_{content.get('name', 'code')}",
                    mime_type=f"text/x-{lang}",
                    description=f"Generated {lang} template",
                    data=code,
                ))

            elif tool_type == "generate_code" and isinstance(content, dict):
                code = content.get("code", "")
                lang = content.get("language", "text")
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.TEXT,
                    name="generated_code",
                    mime_type=f"text/x-{lang}",
                    description=f"AI-generated {lang} code",
                    data=code,
                ))

            elif tool_type == "scaffold_project" and isinstance(content, dict):
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.STRUCTURED_DATA,
                    name="project_scaffold",
                    mime_type="application/json",
                    description=f"Scaffolded project: {content.get('project_name', '')}",
                    data=json.dumps(content),
                ))

            elif tool_type == "implement_section" and isinstance(content, dict):
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.STRUCTURED_DATA,
                    name=f"section_{content.get('section', 'unknown')}",
                    mime_type="application/json",
                    description=f"Implemented section: {content.get('section', '')} ({content.get('tech', '')})",
                    data=json.dumps(content),
                ))

            elif tool_type == "fetch_webpage" and isinstance(content, dict):
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.TEXT,
                    name=content.get("title", "webpage"),
                    mime_type="text/html",
                    description=f"Fetched: {content.get('url', '')}",
                    data=content.get("content", "")[:10000],
                ))

            elif tool_type == "read_file" and isinstance(content, str):
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.TEXT,
                    name="file_content",
                    mime_type="text/plain",
                    description="File content",
                    data=content[:10000],
                ))

            elif tool_type == "list_directory" and isinstance(content, dict):
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.STRUCTURED_DATA,
                    name="directory_listing",
                    mime_type="application/json",
                    description=f"Contents of {content.get('directory', '')}",
                    data=json.dumps(content),
                ))

            elif tool_type == "list_templates" and isinstance(content, dict):
                self.task_manager.add_artifact(task_id, Artifact(
                    type=ArtifactType.STRUCTURED_DATA,
                    name="available_templates",
                    mime_type="application/json",
                    description="Available code and project templates",
                    data=json.dumps(content),
                ))

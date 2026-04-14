"""
CLI Navigator - Hierarchical state machine for browsing tools.
Reads structure from the MCP registry. No tool logic.

States:
    CATEGORIES  → Level 1: list of categories
    TOOLS       → Level 2: tools within a category
    DETAIL      → Level 3: single tool detail + run option
    SEARCH      → Flat search results
"""
from enum import Enum, auto
from typing import List, Optional

from mcp.registry import ToolRegistry, ToolSchema


class State(Enum):
    CATEGORIES = auto()
    TOOLS      = auto()
    DETAIL     = auto()
    SEARCH     = auto()


class Navigator:
    """Schema-driven navigation — no hard-coded tool names."""

    def __init__(self, registry: ToolRegistry):
        self._registry = registry
        self._state: State = State.CATEGORIES

        # Cached from registry (rebuilt on reset)
        self._categories: List[str] = []
        self._tool_counts: dict = {}
        self._current_tools: List[ToolSchema] = []
        self._current_category: Optional[str] = None
        self._current_tool: Optional[ToolSchema] = None
        self._search_results: List[ToolSchema] = []
        self._search_query: str = ""

        self._refresh_categories()

    # ── public accessors ─────────────────────────────────
    @property
    def state(self) -> State:
        return self._state

    @property
    def categories(self) -> List[str]:
        return self._categories

    @property
    def tool_counts(self) -> dict:
        return self._tool_counts

    @property
    def current_tools(self) -> List[ToolSchema]:
        return self._current_tools

    @property
    def current_category(self) -> Optional[str]:
        return self._current_category

    @property
    def current_tool(self) -> Optional[ToolSchema]:
        return self._current_tool

    @property
    def search_results(self) -> List[ToolSchema]:
        return self._search_results

    @property
    def search_query(self) -> str:
        return self._search_query

    @property
    def breadcrumb(self) -> List[str]:
        parts: List[str] = []
        if self._state == State.SEARCH:
            parts.append(f"search: {self._search_query}")
        if self._current_category:
            parts.append(self._current_category)
        if self._current_tool:
            parts.append(self._current_tool.name)
        return parts

    # ── navigation ───────────────────────────────────────
    def select_category(self, index: int) -> bool:
        """Move to TOOLS state for the given category index (1-based)."""
        if 1 <= index <= len(self._categories):
            cat = self._categories[index - 1]
            self._current_category = cat
            self._current_tools = self._registry.get_tools_by_category(cat)
            self._state = State.TOOLS
            return True
        return False

    def select_tool(self, index: int) -> bool:
        """Move to DETAIL state for the given tool index (1-based)."""
        source = self._current_tools if self._state == State.TOOLS else self._search_results
        if 1 <= index <= len(source):
            self._current_tool = source[index - 1]
            self._state = State.DETAIL
            return True
        return False

    def go_back(self):
        """Navigate one level up."""
        if self._state == State.DETAIL:
            self._current_tool = None
            if self._search_results and self._current_category is None:
                self._state = State.SEARCH
            else:
                self._state = State.TOOLS
        elif self._state in (State.TOOLS, State.SEARCH):
            self._current_category = None
            self._current_tools = []
            self._search_results = []
            self._search_query = ""
            self._state = State.CATEGORIES
        # CATEGORIES → no-op (already top)

    def search(self, query: str):
        """Search tools by name or description (case-insensitive)."""
        q = query.lower()
        self._search_results = [
            t for t in self._registry.tools.values()
            if q in t.name.lower() or q in t.description.lower()
        ]
        self._search_query = query
        self._current_category = None
        self._state = State.SEARCH

    # ── internals ────────────────────────────────────────
    def _refresh_categories(self):
        grouped = self._registry.get_categorized_tools()
        self._categories = sorted(grouped.keys())
        self._tool_counts = {cat: len(tools) for cat, tools in grouped.items()}

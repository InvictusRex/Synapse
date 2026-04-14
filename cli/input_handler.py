"""
CLI Input Handler - Parses natural language into tool arguments.

The user types one sentence. This module:
  1. Extracts any save instruction ("save it", "save as X", "save to X")
  2. Uses the LLM to map the remaining text to the tool's parameter schema
  3. Falls back to simple heuristics for single-param tools or key=value input
"""
import json
import os
import re
from typing import Any, Dict, Optional, Tuple

from mcp.registry import ToolSchema


# ---------------------------------------------------------------------------
# Save-instruction extraction
# ---------------------------------------------------------------------------

_SAVE_PATTERNS = [
    r',?\s*(?:and\s+)?save\s+(?:it\s+)?as\s+["\']?([^\s"\']+)["\']?',
    r',?\s*(?:and\s+)?save\s+(?:it\s+)?(?:to|in)\s+(\S+)\s+folder',
    r',?\s*(?:and\s+)?save\s+(?:it\s+)?(?:to|in)\s+["\']?([^\s"\']+)["\']?',
    r',?\s*(?:and\s+)?save\s+(?:it|the\s+\w+)\s*$',
]


def extract_save_path(text: str) -> Tuple[str, Optional[str]]:
    """
    Pull a save instruction out of the user's text.

    Returns (cleaned_text, save_path_or_None).
    """
    for pattern in _SAVE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            cleaned = text[:m.start()].strip().rstrip(",").strip()
            if m.lastindex and m.lastindex >= 1:
                raw_path = m.group(1)
                _, ext = os.path.splitext(raw_path)
                if not ext:
                    return cleaned, raw_path + "/"
                return cleaned, raw_path
            else:
                return cleaned, ""
    return text, None


# ---------------------------------------------------------------------------
# LLM-based argument extraction
# ---------------------------------------------------------------------------

def _build_extraction_prompt(user_text: str, tool: ToolSchema) -> str:
    """Build a prompt that asks the LLM to extract structured args."""
    props = tool.parameters.get("properties", {})
    required = tool.parameters.get("required", [])

    param_lines = []
    for pname, pinfo in props.items():
        ptype = pinfo.get("type", "string")
        pdesc = pinfo.get("description", "")
        req = "REQUIRED" if pname in required else "optional"
        param_lines.append(f'  - {pname} ({ptype}, {req}): {pdesc}')

    params_block = "\n".join(param_lines)

    return f"""Extract structured arguments from the user's natural language input for the tool "{tool.name}".

Tool description: {tool.description}

Parameters:
{params_block}

User input: "{user_text}"

Return ONLY a valid JSON object mapping parameter names to values. Nothing else.
For example: {{"topic": "renewable energy", "context": "focus on solar"}}

If a parameter has no clear value from the input, omit it (unless it is REQUIRED, then infer the best value).
Do NOT include any explanation, markdown, or extra text. Just the JSON object."""


def _extract_args_via_llm(user_text: str, tool: ToolSchema) -> Optional[Dict[str, Any]]:
    """Use the LLM to parse natural language into tool arguments."""
    from mcp.tool_loader import generate_text

    prompt = _build_extraction_prompt(user_text, tool)

    try:
        raw_response = generate_text(prompt, max_tokens=300)
    except Exception:
        return None

    # Parse JSON from response
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object in the response
    match = re.search(r'\{[^{}]+\}', raw_response)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Simple heuristic fallbacks
# ---------------------------------------------------------------------------

def _cast_value(raw: str, ptype: str) -> Any:
    if ptype == "integer":
        return int(raw)
    if ptype == "number":
        return float(raw)
    if ptype == "boolean":
        return raw.lower() in ("true", "1", "yes", "y")
    if ptype in ("object", "array"):
        return json.loads(raw)
    return raw


def _single_param_fallback(text: str, tool: ToolSchema) -> Optional[Dict[str, Any]]:
    """If the tool has exactly one required param, map the whole text to it."""
    props = tool.parameters.get("properties", {})
    required = list(tool.parameters.get("required", []))

    if len(required) == 1:
        ptype = props.get(required[0], {}).get("type", "string")
        try:
            return {required[0]: _cast_value(text, ptype)}
        except (ValueError, json.JSONDecodeError):
            return None
    return None


def _no_params_fallback(tool: ToolSchema) -> Optional[Dict[str, Any]]:
    """If the tool takes no parameters, return empty dict."""
    props = tool.parameters.get("properties", {})
    if not props:
        return {}
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def try_inline_execution(raw_input: str, tool: ToolSchema) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parse user's natural language input into tool arguments + save path.

    Returns (args_dict_or_None, save_path_or_None).
    """
    # 1. Extract save instruction
    text, save_path = extract_save_path(raw_input)

    # 2. No-param tools
    no_param = _no_params_fallback(tool)
    if no_param is not None:
        return no_param, save_path

    # 3. Single required param — just use the whole text
    single = _single_param_fallback(text, tool)
    if single is not None:
        return single, save_path

    # 4. Multi-param tools — use LLM to extract structured args
    llm_args = _extract_args_via_llm(text, tool)
    if llm_args is not None:
        return llm_args, save_path

    # 5. Last resort — shove everything into the first required param
    required = list(tool.parameters.get("required", []))
    if required:
        return {required[0]: text}, save_path

    return None, None

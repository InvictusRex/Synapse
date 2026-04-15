"""
Synapse Configuration
Multi-LLM support with fallback
"""
import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# LLM Models
GROQ_MODEL = "llama-3.1-8b-instant"
GEMINI_MODEL = "gemini-2.0-flash"

# LLM Priority (first = primary, rest = fallbacks)
LLM_PRIORITY = ["groq", "gemini"]

# LLM Pool Settings
LLM_POOL_SIZE = 3  # Number of concurrent LLM workers
LLM_TIMEOUT = 30   # Timeout in seconds
LLM_MAX_RETRIES = 2

# =============================================================================
# DAG EXECUTOR CONFIGURATION
# =============================================================================

DAG_MAX_WORKERS = 4  # Max parallel task workers
DAG_TASK_TIMEOUT = 60  # Task timeout in seconds

# =============================================================================
# MEMORY CONFIGURATION
# =============================================================================

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory_store')
MEMORY_FILE = os.path.join(MEMORY_DIR, 'persistent_memory.json')
VECTOR_MEMORY_FILE = os.path.join(MEMORY_DIR, 'vector_memory.json')
MEMORY_MAX_ENTRIES = 1000

# =============================================================================
# A2A SERVER CONFIGURATION
# =============================================================================

A2A_SERVER_HOST = "127.0.0.1"
A2A_SERVER_PORT = 8765
A2A_SERVER_ENABLED = False

# =============================================================================
# MCP CONFIGURATION
# =============================================================================

MCP_TOOLS_ENABLED = True

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

import os
from dotenv import load_dotenv

load_dotenv()

# LLM Configuration - supports both Groq and Gemini
# Set ONE of these API keys:
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model settings
GROQ_MODEL = "llama-3.1-8b-instant"  # Fast and capable
GEMINI_MODEL = "gemini-1.5-flash"    # Fast and free tier friendly

# Auto-detect which provider to use
LLM_PROVIDER = "gemini" if GEMINI_API_KEY else "groq"

# System settings
MAX_RETRIES = 2
TIMEOUT_SECONDS = 30

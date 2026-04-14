import os
from dotenv import load_dotenv

load_dotenv()

# LLM Configuration (using Groq - free and fast)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = "llama-3.1-8b-instant"  # Fast and capable

# System settings
MAX_RETRIES = 2
TIMEOUT_SECONDS = 30

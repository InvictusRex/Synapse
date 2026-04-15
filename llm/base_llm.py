"""
Base LLM Interface
Abstract class for all LLM implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import time


class LLMStatus(Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    success: bool
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "error": self.error
        }


@dataclass  
class LLMConfig:
    """LLM Configuration"""
    api_key: str
    model: str
    max_tokens: int = 1500
    temperature: float = 0.3
    timeout: int = 30


class BaseLLM(ABC):
    """
    Abstract Base Class for LLM implementations
    
    All LLM providers must implement:
    - generate(): Main text generation method
    - health_check(): Check if LLM is available
    - get_status(): Get current status
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.status = LLMStatus.AVAILABLE
        self.last_error: Optional[str] = None
        self.request_count = 0
        self.error_count = 0
        self.total_latency = 0.0
        self._last_request_time = 0
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'groq', 'gemini')"""
        pass
    
    @abstractmethod
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """
        Internal API call - must be implemented by each provider
        """
        pass
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """
        Generate text from the LLM
        Handles timing, error tracking, and status updates
        """
        start_time = time.time()
        self._last_request_time = start_time
        
        try:
            self.status = LLMStatus.BUSY
            response = self._call_api(prompt, system_prompt)
            
            # Update stats
            latency = (time.time() - start_time) * 1000
            response.latency_ms = latency
            self.request_count += 1
            self.total_latency += latency
            
            if response.success:
                self.status = LLMStatus.AVAILABLE
                self.last_error = None
            else:
                self.error_count += 1
                self.last_error = response.error
                self.status = LLMStatus.ERROR
            
            return response
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            self.status = LLMStatus.ERROR
            
            return LLMResponse(
                success=False,
                content="",
                model=self.config.model,
                provider=self.provider_name,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    def health_check(self) -> bool:
        """Check if the LLM is healthy and available"""
        try:
            response = self.generate("Say 'ok' if you are working.")
            return response.success and len(response.content) > 0
        except:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current LLM status and stats"""
        avg_latency = self.total_latency / max(self.request_count, 1)
        return {
            "provider": self.provider_name,
            "model": self.config.model,
            "status": self.status.value,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "avg_latency_ms": round(avg_latency, 2),
            "last_error": self.last_error
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.request_count = 0
        self.error_count = 0
        self.total_latency = 0.0
        self.last_error = None

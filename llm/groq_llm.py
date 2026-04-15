"""
Groq LLM Implementation
Fast inference with Llama models
"""
from typing import Optional
from llm.base_llm import BaseLLM, LLMConfig, LLMResponse, LLMStatus


class GroqLLM(BaseLLM):
    """
    Groq LLM Provider
    Uses Groq's fast inference API
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    @property
    def provider_name(self) -> str:
        return "groq"
    
    def _get_client(self):
        """Lazy load Groq client"""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("groq package not installed. Run: pip install groq")
        return self._client
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Call Groq API"""
        try:
            client = self._get_client()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            
            return LLMResponse(
                success=True,
                content=content,
                model=self.config.model,
                provider=self.provider_name,
                tokens_used=tokens
            )
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for rate limiting
            if "rate" in error_msg.lower() or "429" in error_msg:
                self.status = LLMStatus.RATE_LIMITED
            
            return LLMResponse(
                success=False,
                content="",
                model=self.config.model,
                provider=self.provider_name,
                error=error_msg
            )


def create_groq_llm(api_key: str, model: str = "llama-3.1-8b-instant") -> GroqLLM:
    """Factory function to create Groq LLM"""
    config = LLMConfig(
        api_key=api_key,
        model=model,
        max_tokens=1500,
        temperature=0.3
    )
    return GroqLLM(config)

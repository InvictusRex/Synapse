"""
Gemini LLM Implementation
Google's Gemini API with fallback support
Supports both google-genai (new) and google-generativeai (legacy)
"""
from typing import Optional
from llm.base_llm import BaseLLM, LLMConfig, LLMResponse, LLMStatus


class GeminiLLM(BaseLLM):
    """
    Gemini LLM Provider
    Uses Google's Gemini API
    Supports both new (google-genai) and legacy (google-generativeai) SDKs
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
        self._sdk_type = None  # 'new' or 'legacy'
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    def _init_client(self):
        """Initialize Gemini client with fallback"""
        if self._client is not None:
            return
        
        # Try new SDK first (google-genai)
        try:
            from google import genai
            self._client = genai.Client(api_key=self.config.api_key)
            self._sdk_type = "new"
            return
        except ImportError:
            pass
        except Exception:
            pass
        
        # Fallback to legacy SDK (google-generativeai)
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            self._client = genai.GenerativeModel(self.config.model)
            self._sdk_type = "legacy"
            return
        except ImportError:
            raise ImportError(
                "Neither google-genai nor google-generativeai installed. "
                "Run: pip install google-genai or pip install google-generativeai"
            )
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Call Gemini API"""
        try:
            self._init_client()
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
            
            if self._sdk_type == "new":
                return self._call_new_sdk(full_prompt)
            else:
                return self._call_legacy_sdk(full_prompt)
                
        except Exception as e:
            error_msg = str(e)
            
            # Check for rate limiting
            if "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                self.status = LLMStatus.RATE_LIMITED
            
            return LLMResponse(
                success=False,
                content="",
                model=self.config.model,
                provider=self.provider_name,
                error=error_msg
            )
    
    def _call_new_sdk(self, prompt: str) -> LLMResponse:
        """Call using new google-genai SDK"""
        try:
            response = self._client.models.generate_content(
                model=self.config.model,
                contents=prompt,
                config={
                    "max_output_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature
                }
            )
            
            content = response.text if hasattr(response, 'text') else str(response)
            
            return LLMResponse(
                success=True,
                content=content,
                model=self.config.model,
                provider=self.provider_name,
                tokens_used=0  # New SDK token counting varies
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                content="",
                model=self.config.model,
                provider=self.provider_name,
                error=str(e)
            )
    
    def _call_legacy_sdk(self, prompt: str) -> LLMResponse:
        """Call using legacy google-generativeai SDK"""
        try:
            import google.generativeai as genai
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            response = self._client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            content = response.text
            
            return LLMResponse(
                success=True,
                content=content,
                model=self.config.model,
                provider=self.provider_name,
                tokens_used=0
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                content="",
                model=self.config.model,
                provider=self.provider_name,
                error=str(e)
            )


def create_gemini_llm(api_key: str, model: str = "gemini-2.0-flash") -> GeminiLLM:
    """Factory function to create Gemini LLM"""
    config = LLMConfig(
        api_key=api_key,
        model=model,
        max_tokens=1500,
        temperature=0.3
    )
    return GeminiLLM(config)

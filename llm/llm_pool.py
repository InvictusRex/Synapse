"""
LLM Pool Manager
Manages multiple LLMs with fallback, load balancing, and parallel execution
"""
import os
import threading
from typing import Dict, Any, Optional, List, Callable
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from queue import Queue, Empty
import time

from llm.base_llm import BaseLLM, LLMResponse, LLMStatus, LLMConfig
from llm.groq_llm import GroqLLM, create_groq_llm
from llm.gemini_llm import GeminiLLM, create_gemini_llm


class LLMPool:
    """
    LLM Pool Manager
    
    Features:
    - Multiple LLM providers with automatic fallback
    - Load balancing across available LLMs
    - Parallel request execution
    - Health monitoring and auto-recovery
    - Thread-safe operations
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._llms: Dict[str, BaseLLM] = {}
        self._priority: List[str] = []
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._request_queue = Queue()
        self._lock = threading.Lock()
        self._initialized = True
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_count": 0
        }
    
    def register_llm(self, name: str, llm: BaseLLM, priority: int = None):
        """
        Register an LLM provider
        
        Args:
            name: Unique identifier for this LLM
            llm: LLM instance
            priority: Priority order (lower = higher priority)
        """
        with self._lock:
            self._llms[name] = llm
            if name not in self._priority:
                if priority is not None and priority < len(self._priority):
                    self._priority.insert(priority, name)
                else:
                    self._priority.append(name)
    
    def unregister_llm(self, name: str):
        """Remove an LLM from the pool"""
        with self._lock:
            if name in self._llms:
                del self._llms[name]
            if name in self._priority:
                self._priority.remove(name)
    
    def initialize_defaults(self):
        """Initialize with default LLMs from environment"""
        groq_key = os.environ.get("GROQ_API_KEY", "")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        
        if groq_key:
            try:
                groq = create_groq_llm(groq_key)
                self.register_llm("groq", groq, priority=0)
            except Exception as e:
                print(f"[LLMPool] Failed to init Groq: {e}")
        
        if gemini_key:
            try:
                gemini = create_gemini_llm(gemini_key)
                self.register_llm("gemini", gemini, priority=1)
            except Exception as e:
                print(f"[LLMPool] Failed to init Gemini: {e}")
        
        if not self._llms:
            raise RuntimeError("No LLMs available. Set GROQ_API_KEY or GEMINI_API_KEY")
    
    def get_available_llm(self) -> Optional[BaseLLM]:
        """Get the highest priority available LLM"""
        with self._lock:
            for name in self._priority:
                llm = self._llms.get(name)
                if llm and llm.status in [LLMStatus.AVAILABLE, LLMStatus.BUSY]:
                    return llm
        return None
    
    def get_llm_by_name(self, name: str) -> Optional[BaseLLM]:
        """Get a specific LLM by name"""
        return self._llms.get(name)
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                 preferred_llm: str = None) -> LLMResponse:
        """
        Generate text with automatic fallback
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            preferred_llm: Preferred LLM to use (falls back if unavailable)
        
        Returns:
            LLMResponse from the first successful LLM
        """
        self._stats["total_requests"] += 1
        
        # Build LLM order
        llm_order = list(self._priority)
        if preferred_llm and preferred_llm in llm_order:
            llm_order.remove(preferred_llm)
            llm_order.insert(0, preferred_llm)
        
        last_error = None
        used_fallback = False
        
        for i, name in enumerate(llm_order):
            llm = self._llms.get(name)
            if not llm:
                continue
            
            if llm.status == LLMStatus.UNAVAILABLE:
                continue
            
            if i > 0:
                used_fallback = True
            
            response = llm.generate(prompt, system_prompt)
            
            if response.success:
                self._stats["successful_requests"] += 1
                if used_fallback:
                    self._stats["fallback_count"] += 1
                return response
            
            last_error = response.error
        
        # All LLMs failed
        self._stats["failed_requests"] += 1
        return LLMResponse(
            success=False,
            content="",
            model="none",
            provider="none",
            error=f"All LLMs failed. Last error: {last_error}"
        )
    
    def generate_parallel(self, prompts: List[Dict[str, Any]]) -> List[LLMResponse]:
        """
        Generate multiple prompts in parallel across available LLMs
        
        Args:
            prompts: List of dicts with 'prompt' and optional 'system_prompt', 'id'
        
        Returns:
            List of LLMResponses in same order as input
        """
        results = [None] * len(prompts)
        futures: Dict[Future, int] = {}
        
        # Distribute work across LLMs
        available_llms = [name for name in self._priority 
                        if self._llms.get(name) and 
                        self._llms[name].status != LLMStatus.UNAVAILABLE]
        
        if not available_llms:
            return [LLMResponse(
                success=False, content="", model="none", 
                provider="none", error="No LLMs available"
            ) for _ in prompts]
        
        def generate_with_llm(idx: int, prompt_data: Dict, llm_name: str):
            prompt = prompt_data.get("prompt", "")
            system_prompt = prompt_data.get("system_prompt")
            return idx, self.generate(prompt, system_prompt, preferred_llm=llm_name)
        
        # Submit all tasks
        for i, prompt_data in enumerate(prompts):
            # Round-robin across LLMs for load balancing
            llm_name = available_llms[i % len(available_llms)]
            future = self._executor.submit(generate_with_llm, i, prompt_data, llm_name)
            futures[future] = i
        
        # Collect results
        for future in as_completed(futures):
            try:
                idx, response = future.result(timeout=60)
                results[idx] = response
            except Exception as e:
                idx = futures[future]
                results[idx] = LLMResponse(
                    success=False, content="", model="none",
                    provider="none", error=str(e)
                )
        
        return results
    
    def health_check_all(self) -> Dict[str, bool]:
        """Run health check on all LLMs"""
        results = {}
        for name, llm in self._llms.items():
            try:
                results[name] = llm.health_check()
            except:
                results[name] = False
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        llm_stats = {}
        for name, llm in self._llms.items():
            llm_stats[name] = llm.get_status()
        
        return {
            "pool_stats": self._stats,
            "llm_count": len(self._llms),
            "priority_order": self._priority,
            "llm_details": llm_stats
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_count": 0
        }
        for llm in self._llms.values():
            llm.reset_stats()
    
    def shutdown(self):
        """Shutdown the pool"""
        self._executor.shutdown(wait=False)


# Global pool instance
_pool: Optional[LLMPool] = None

def get_llm_pool() -> LLMPool:
    """Get or create the global LLM pool"""
    global _pool
    if _pool is None:
        _pool = LLMPool()
    return _pool

def init_llm_pool():
    """Initialize the global LLM pool with defaults"""
    pool = get_llm_pool()
    pool.initialize_defaults()
    return pool

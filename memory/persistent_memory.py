"""
Persistent Memory System
File-based and vector memory for context retention
"""
import os
import json
import threading
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import math


@dataclass
class MemoryEntry:
    """A single memory entry"""
    id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    embedding: Optional[List[float]] = None
    access_count: int = 0
    last_accessed: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        return cls(**data)


class PersistentMemory:
    """
    File-based persistent memory
    
    Features:
    - JSON-based storage
    - Automatic persistence
    - Memory search and retrieval
    - Memory decay and cleanup
    """
    
    def __init__(self, storage_path: str, max_entries: int = 1000):
        self.storage_path = storage_path
        self.max_entries = max_entries
        self._memory: Dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()
        self._dirty = False
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Load existing memory
        self._load()
    
    def _load(self):
        """Load memory from disk"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_data in data.get("entries", []):
                        entry = MemoryEntry.from_dict(entry_data)
                        self._memory[entry.id] = entry
            except Exception as e:
                print(f"[Memory] Failed to load: {e}")
    
    def _save(self):
        """Save memory to disk"""
        if not self._dirty:
            return
        
        try:
            data = {
                "version": "1.0",
                "updated": datetime.now().isoformat(),
                "entries": [entry.to_dict() for entry in self._memory.values()]
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self._dirty = False
        except Exception as e:
            print(f"[Memory] Failed to save: {e}")
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Store a memory entry"""
        with self._lock:
            entry_id = self._generate_id(content)
            
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                metadata=metadata or {},
                timestamp=datetime.now().isoformat(),
                access_count=0
            )
            
            self._memory[entry_id] = entry
            self._dirty = True
            
            # Cleanup if over limit
            if len(self._memory) > self.max_entries:
                self._cleanup()
            
            self._save()
            return entry_id
    
    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID"""
        with self._lock:
            entry = self._memory.get(entry_id)
            if entry:
                entry.access_count += 1
                entry.last_accessed = datetime.now().isoformat()
                self._dirty = True
            return entry
    
    def search(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """Search memories by content (simple text matching)"""
        query_lower = query.lower()
        results = []
        
        with self._lock:
            for entry in self._memory.values():
                if query_lower in entry.content.lower():
                    results.append(entry)
                elif any(query_lower in str(v).lower() for v in entry.metadata.values()):
                    results.append(entry)
        
        # Sort by access count (most accessed first)
        results.sort(key=lambda e: e.access_count, reverse=True)
        return results[:limit]
    
    def search_by_metadata(self, key: str, value: Any) -> List[MemoryEntry]:
        """Search memories by metadata"""
        results = []
        with self._lock:
            for entry in self._memory.values():
                if entry.metadata.get(key) == value:
                    results.append(entry)
        return results
    
    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        """Get most recent memories"""
        with self._lock:
            sorted_entries = sorted(
                self._memory.values(),
                key=lambda e: e.timestamp,
                reverse=True
            )
            return sorted_entries[:limit]
    
    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry"""
        with self._lock:
            if entry_id in self._memory:
                del self._memory[entry_id]
                self._dirty = True
                self._save()
                return True
            return False
    
    def _cleanup(self):
        """Remove least accessed entries"""
        if len(self._memory) <= self.max_entries:
            return
        
        # Sort by access count and timestamp
        sorted_entries = sorted(
            self._memory.items(),
            key=lambda x: (x[1].access_count, x[1].timestamp)
        )
        
        # Remove oldest/least accessed
        to_remove = len(self._memory) - self.max_entries
        for i in range(to_remove):
            del self._memory[sorted_entries[i][0]]
        
        self._dirty = True
    
    def clear(self):
        """Clear all memory"""
        with self._lock:
            self._memory.clear()
            self._dirty = True
            self._save()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        with self._lock:
            return {
                "total_entries": len(self._memory),
                "max_entries": self.max_entries,
                "storage_path": self.storage_path
            }
    
    def export(self) -> List[Dict]:
        """Export all memories"""
        with self._lock:
            return [entry.to_dict() for entry in self._memory.values()]


class VectorMemory:
    """
    Simple vector-based memory using cosine similarity
    No external dependencies - uses basic text features
    """
    
    def __init__(self, storage_path: str, max_entries: int = 500):
        self.storage_path = storage_path
        self.max_entries = max_entries
        self._entries: Dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()
        
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        self._load()
    
    def _load(self):
        """Load from disk"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_data in data.get("entries", []):
                        entry = MemoryEntry.from_dict(entry_data)
                        self._entries[entry.id] = entry
            except Exception:
                pass
    
    def _save(self):
        """Save to disk"""
        try:
            data = {
                "version": "1.0",
                "entries": [e.to_dict() for e in self._entries.values()]
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    def _text_to_vector(self, text: str) -> List[float]:
        """
        Convert text to a simple feature vector
        Uses character n-grams and word features
        """
        text = text.lower()
        words = text.split()
        
        # Simple features
        features = []
        
        # Word count features
        features.append(len(words) / 100.0)  # Normalized word count
        features.append(len(text) / 1000.0)  # Normalized char count
        
        # Character frequency (a-z)
        char_freq = [0.0] * 26
        for c in text:
            if 'a' <= c <= 'z':
                char_freq[ord(c) - ord('a')] += 1
        total = sum(char_freq) or 1
        features.extend([f / total for f in char_freq])
        
        # Common word presence
        common_words = ['the', 'a', 'is', 'are', 'was', 'were', 'be', 'been',
                       'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                       'could', 'should', 'may', 'might', 'must', 'can']
        for word in common_words:
            features.append(1.0 if word in words else 0.0)
        
        return features
    
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(v1) != len(v2):
            return 0.0
        
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(a * a for a in v1))
        mag2 = math.sqrt(sum(b * b for b in v2))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot / (mag1 * mag2)
    
    def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Store with vector embedding"""
        with self._lock:
            entry_id = hashlib.md5(content.encode()).hexdigest()[:12]
            embedding = self._text_to_vector(content)
            
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                metadata=metadata or {},
                timestamp=datetime.now().isoformat(),
                embedding=embedding
            )
            
            self._entries[entry_id] = entry
            
            # Cleanup if needed
            if len(self._entries) > self.max_entries:
                oldest = min(self._entries.values(), key=lambda e: e.timestamp)
                del self._entries[oldest.id]
            
            self._save()
            return entry_id
    
    def search_similar(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """Find similar memories using vector similarity"""
        query_vector = self._text_to_vector(query)
        
        similarities = []
        with self._lock:
            for entry in self._entries.values():
                if entry.embedding:
                    sim = self._cosine_similarity(query_vector, entry.embedding)
                    similarities.append((entry, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in similarities[:limit]]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "max_entries": self.max_entries
        }


# Global memory instances
_persistent_memory: Optional[PersistentMemory] = None
_vector_memory: Optional[VectorMemory] = None

def get_persistent_memory(storage_path: str = None) -> PersistentMemory:
    """Get or create persistent memory"""
    global _persistent_memory
    if _persistent_memory is None:
        from config import MEMORY_FILE
        path = storage_path or MEMORY_FILE
        _persistent_memory = PersistentMemory(path)
    return _persistent_memory

def get_vector_memory(storage_path: str = None) -> VectorMemory:
    """Get or create vector memory"""
    global _vector_memory
    if _vector_memory is None:
        from config import VECTOR_MEMORY_FILE
        path = storage_path or VECTOR_MEMORY_FILE
        _vector_memory = VectorMemory(path)
    return _vector_memory

"""
Shared Memory Manager - shared memory between agents

Based on Day 3b: Memory Management
Provides shared memory between agents for context exchange.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from observability.logging import get_logger

logger = get_logger(__name__)


class SharedMemoryManager:
    """
    Shared memory manager for context exchange between agents.
    
    Used for:
    - Data exchange between agents in one pipeline
    - Caching results between sessions
    - Storing intermediate processing results
    """
    
    def __init__(self):
        """Initialize SharedMemoryManager."""
        # In-memory storage (can be extended to Redis/Firestore)
        self._memory: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._ttl: Dict[str, datetime] = {}
        logger.info("SharedMemoryManager initialized")
    
    def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Sets value in shared memory.
        
        Args:
            key: Key for storage
            value: Value to store
            namespace: Namespace (for isolation between agents)
            ttl_seconds: Time to live in seconds (optional)
        """
        full_key = f"{namespace}:{key}"
        self._memory[namespace][key] = value
        
        if ttl_seconds:
            self._ttl[full_key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        logger.debug(f"Shared memory set: {full_key}", extra={
            "event_type": "shared_memory_set",
            "namespace": namespace,
            "key": key
        })
    
    def get(
        self,
        key: str,
        namespace: str = "default",
        default: Any = None
    ) -> Any:
        """Gets value from shared memory.
        
        Args:
            key: Key to get
            namespace: Namespace
            default: Default value if key not found
            
        Returns:
            Value or default
        """
        full_key = f"{namespace}:{key}"
        
        if full_key in self._ttl:
            if datetime.utcnow() > self._ttl[full_key]:
                del self._ttl[full_key]
                if key in self._memory[namespace]:
                    del self._memory[namespace][key]
                return default
        
        value = self._memory[namespace].get(key, default)
        
        if value is not None:
            logger.debug(f"Shared memory get: {full_key}", extra={
                "event_type": "shared_memory_get",
                "namespace": namespace,
                "key": key
            })
        
        return value
    
    def get_all(self, namespace: str = "default") -> Dict[str, Any]:
        """Gets all values from namespace.
        
        Args:
            namespace: Namespace
            
        Returns:
            Dictionary with all values in namespace
        """
        # Cleanup expired TTL
        self._cleanup_expired()
        
        return dict(self._memory[namespace])
    
    def delete(self, key: str, namespace: str = "default") -> bool:
        """Deletes value from shared memory.
        
        Args:
            key: Key to delete
            namespace: Namespace
            
        Returns:
            True if key was deleted, False if not found
        """
        full_key = f"{namespace}:{key}"
        
        if key in self._memory[namespace]:
            del self._memory[namespace][key]
            if full_key in self._ttl:
                del self._ttl[full_key]
            
            logger.debug(f"Shared memory deleted: {full_key}", extra={
                "event_type": "shared_memory_delete",
                "namespace": namespace,
                "key": key
            })
            
            return True
        
        return False
    
    def clear_namespace(self, namespace: str) -> None:
        """Clears all values in namespace.
        
        Args:
            namespace: Namespace to clear
        """
        if namespace in self._memory:
            del self._memory[namespace]
        
        # Remove TTL for this namespace
        keys_to_delete = [k for k in self._ttl.keys() if k.startswith(f"{namespace}:")]
        for k in keys_to_delete:
            del self._ttl[k]
        
        logger.info(f"Shared memory namespace cleared: {namespace}", extra={
            "event_type": "shared_memory_clear",
            "namespace": namespace
        })
    
    def _cleanup_expired(self) -> None:
        """Cleans up expired records."""
        now = datetime.utcnow()
        expired_keys = [k for k, expiry in self._ttl.items() if now > expiry]
        
        for full_key in expired_keys:
            namespace, key = full_key.split(":", 1)
            if key in self._memory[namespace]:
                del self._memory[namespace][key]
            del self._ttl[full_key]
    
    def share_between_agents(
        self,
        from_agent: str,
        to_agent: str,
        data: Dict[str, Any]
    ) -> None:
        """Shares data between agents.
        
        Args:
            from_agent: Sender agent name
            to_agent: Receiver agent name
            data: Data to share
        """
        namespace = f"agent_{to_agent}"
        
        for key, value in data.items():
            self.set(key, value, namespace=namespace, ttl_seconds=3600)  # 1 hour TTL
        
        logger.info(f"Data shared from {from_agent} to {to_agent}", extra={
            "event_type": "shared_memory_share",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "keys_count": len(data)
        })


# Global instance for use in all agents
_global_shared_memory: Optional[SharedMemoryManager] = None


def get_shared_memory() -> SharedMemoryManager:
    """Gets global SharedMemoryManager instance.
    
    Returns:
        SharedMemoryManager instance
    """
    global _global_shared_memory
    
    if _global_shared_memory is None:
        _global_shared_memory = SharedMemoryManager()
    
    return _global_shared_memory


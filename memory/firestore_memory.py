"""
Firestore Memory Service - long-term memory via Firestore

Based on Day 3b: Memory Management
Uses Firestore for persistent storage of long-term agent memory.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from google.cloud import firestore
    from google.adk.memory import BaseMemoryService
    HAS_FIRESTORE = True
    HAS_ADK_MEMORY = True
except ImportError:
    HAS_FIRESTORE = False
    HAS_ADK_MEMORY = False
    BaseMemoryService = object

from observability.logging import get_logger

logger = get_logger(__name__)


class FirestoreMemoryService(BaseMemoryService):
    """
    Memory Service based on Firestore for long-term memory.
    
    Stores:
    - Consolidated facts from sessions
    - Article metadata (for quick access)
    - Context for agents
    
    Firestore structure:
    - memory/facts/ - consolidated facts
    - memory/articles/ - article references (for quick search)
    - memory/context/ - context for agents
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize Firestore Memory Service.
        
        Args:
            project_id: GCP project ID (if None, uses environment)
        """
        if not HAS_FIRESTORE:
            raise ImportError("google-cloud-firestore not installed")
        
        if not HAS_ADK_MEMORY:
            raise ImportError("google-adk not installed or version does not support memory")
        
        try:
            if project_id:
                self.db = firestore.Client(project=project_id)
            else:
                self.db = firestore.Client()
            
            self.project_id = project_id or self.db.project
            logger.info(f"FirestoreMemoryService initialized for project: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize FirestoreMemoryService: {e}")
            raise
    
    async def add_session_to_memory(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        consolidation_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Adds session data to long-term memory.
        
        Args:
            app_name: Application name
            user_id: User ID
            session_id: Session ID
            consolidation_config: Consolidation configuration (optional)
            
        Returns:
            Dictionary with operation result
        """
        try:
            memory_doc = {
                "app_name": app_name,
                "user_id": user_id,
                "session_id": session_id,
                "consolidated_at": firestore.SERVER_TIMESTAMP,
                "type": "session_consolidation"
            }
            
            memory_ref = self.db.collection("memory").document(f"{app_name}_{user_id}_{session_id}")
            memory_ref.set(memory_doc, merge=True)
            
            logger.info(f"Session {session_id} added to memory", extra={
                "event_type": "memory_added",
                "app_name": app_name,
                "user_id": user_id,
                "session_id": session_id
            })
            
            return {
                "status": "success",
                "memory_id": memory_ref.id
            }
        except Exception as e:
            logger.error(f"Error adding session to memory: {e}", exc_info=True)
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    async def search_memory(
        self,
        app_name: str,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search in long-term memory.
        
        Args:
            app_name: Application name
            user_id: User ID
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of dictionaries with found memory records
        """
        try:
            results = []
            
            # Search in consolidated facts
            facts_ref = self.db.collection("memory").where("app_name", "==", app_name)
            if user_id:
                facts_ref = facts_ref.where("user_id", "==", user_id)
            
            # Simple text search (use semantic search in production)
            for doc in facts_ref.limit(limit).stream():
                doc_data = doc.to_dict()
                if query.lower() in str(doc_data).lower():
                    results.append({
                        "id": doc.id,
                        "data": doc_data,
                        "relevance_score": 0.5  # Simple search, no scoring
                    })
            
            # Also search in articles
            articles_ref = self.db.collection("articles")
            for doc in articles_ref.where("title", ">=", query).where("title", "<=", query + "\uf8ff").limit(limit).stream():
                doc_data = doc.to_dict()
                results.append({
                    "id": doc.id,
                    "type": "article",
                    "data": doc_data,
                    "relevance_score": 0.7
                })
            
            logger.info(f"Memory search completed: {len(results)} results", extra={
                "event_type": "memory_search",
                "app_name": app_name,
                "query": query,
                "results_count": len(results)
            })
            
            return results[:limit]
        except Exception as e:
            logger.error(f"Error searching memory: {e}", exc_info=True)
            return []
    
    def add_article_reference(
        self,
        article_id: str,
        article_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adds article reference to memory for quick access.
        
        Args:
            article_id: Article ID
            article_data: Article data (url, title, summary, key_points)
            
        Returns:
            Dictionary with result
        """
        try:
            memory_ref = self.db.collection("memory").document(f"article_{article_id}")
            
            memory_data = {
                "type": "article_reference",
                "article_id": article_id,
                "url": article_data.get("url"),
                "title": article_data.get("title"),
                "summary": article_data.get("summary", "")[:500],  # Limit size
                "key_points": article_data.get("key_points", [])[:10],  # First 10 points
                "intents": article_data.get("intents", []),
                "values": article_data.get("values", []),
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            
            memory_ref.set(memory_data, merge=True)
            
            logger.info(f"Article reference added to memory: {article_id}")
            
            return {
                "status": "success",
                "memory_id": memory_ref.id
            }
        except Exception as e:
            logger.error(f"Error adding article reference: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }


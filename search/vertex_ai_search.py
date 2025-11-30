"""Vertex AI Search integration for semantic search"""

import os
import logging
from typing import List, Dict, Any, Optional

try:
    from google.cloud import discoveryengine
    from google.cloud.discoveryengine import SearchRequest, SearchResponse
    HAS_DISCOVERY_ENGINE = True
except ImportError:
    HAS_DISCOVERY_ENGINE = False
    logging.warning("google-cloud-discoveryengine not installed. Install: pip install google-cloud-discoveryengine")

try:
    from core.config import GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION
except ImportError:
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "global")

logger = logging.getLogger(__name__)


class VertexAISearch:
    """Semantic search via Vertex AI Search (RAG)"""
    
    def __init__(
        self, 
        project_id: Optional[str] = None, 
        location: Optional[str] = None,
        data_store_id: Optional[str] = None
    ):
        """Initialize Vertex AI Search.
        
        Args:
            project_id: GCP project ID
            location: Location (e.g., us-central1 or global)
            data_store_id: Data Store ID (e.g., tabsage-articles)
        """
        if not HAS_DISCOVERY_ENGINE:
            raise ImportError("google-cloud-discoveryengine not installed")
        
        self.project_id = project_id or GOOGLE_CLOUD_PROJECT
        self.location = location or "global"  # Default global
        self.data_store_id = data_store_id or "tabsage-articles"
        
        self.parent = f"projects/{self.project_id}/locations/{self.location}/dataStores/{self.data_store_id}"
        
        try:
            from google.cloud.discoveryengine import SearchServiceClient
            self.client = SearchServiceClient()
            logger.info(f"Vertex AI Search initialized: {self.parent}")
        except Exception as e:
            logger.warning(f"Failed to initialize SearchServiceClient: {e}")
            self.client = None
    
    def search_articles(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Semantic search for articles via Vertex AI Search.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of articles with relevance
        """
        if not self.client:
            logger.warning("SearchServiceClient not initialized, returning empty results")
            return []
        
        try:
            from google.cloud.discoveryengine import SearchRequest
            
            request = SearchRequest(
                parent=self.parent,
                query=query,
                page_size=limit
            )
            
            response = self.client.search(request=request)
            
            results = []
            for result in response.results:
                document = result.document
                article_data = {
                    "title": getattr(document, "title", ""),
                    "url": getattr(document, "uri", ""),
                    "summary": getattr(document, "struct_data", {}).get("summary", ""),
                    "relevance_score": result.relevance_score if hasattr(result, "relevance_score") else 0.0,
                    "id": document.id if hasattr(document, "id") else ""
                }
                results.append(article_data)
            
            logger.info(f"Found {len(results)} articles for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching articles: {e}")
            return []
    
    def get_relevant_summaries(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Gets relevant summaries by topic.
        
        Args:
            topic: Topic to search
            limit: Maximum number of results
            
        Returns:
            List of summaries with relevance
        """
        # TODO: Implement via Vertex AI Search
        return []


def create_vertex_search(
    project_id: Optional[str] = None, 
    location: Optional[str] = None,
    data_store_id: Optional[str] = None
) -> Optional[VertexAISearch]:
    """Creates Vertex AI Search client.
    
    Args:
        project_id: Project ID (default from config)
        location: Location (default "global")
        data_store_id: Data Store ID (default "tabsage-articles")
        
    Returns:
        VertexAISearch or None if not configured
    """
    try:
        return VertexAISearch(
            project_id=project_id, 
            location=location,
            data_store_id=data_store_id
        )
    except ImportError:
        logger.warning("Vertex AI Search not available")
        return None


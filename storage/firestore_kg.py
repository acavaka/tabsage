"""
Firestore Knowledge Graph - persistent knowledge graph storage

Knowledge Graph implementation based on Google Cloud Firestore for persistent
storage of entities, relationships, and articles.

Architecture:
- Uses Firestore collections: entities, relations, articles
- Automatic initialization via Application Default Credentials
- Async operations support for performance
- Indexing for fast search

Data structure:
- entities: Graph entities (type, canonical_name, aliases, confidence)
- relations: Relationships between entities (subject, predicate, object, confidence)
- articles: Processed articles (url, title, summary, key_points, etc.)

Features:
- Automatic update of existing entities (merge aliases)
- Article search with relevance scoring
- Related article search using embeddings
- Real-time graph statistics

Usage:
    from storage.firestore_kg import FirestoreKnowledgeGraph
    
    kg = FirestoreKnowledgeGraph()
    await kg.add_entity({"type": "CONCEPT", "canonical_name": "AI"})
    articles = await kg.search_articles_by_topic("microservices", limit=5)
"""

import logging
from typing import Dict, Any, Optional, List, Set
from collections import defaultdict

try:
    from google.cloud import firestore
    HAS_FIRESTORE = True
except ImportError:
    HAS_FIRESTORE = False
    logging.warning("google-cloud-firestore not installed. Install: pip install google-cloud-firestore")

logger = logging.getLogger(__name__)


class FirestoreKnowledgeGraph:
    """Knowledge Graph in Cloud Firestore.
    
    Structure:
    - articles/ - processed articles
    - entities/ - graph entities
    - relations/ - relationships between entities
    - topics/ - topics and clusters
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize Firestore client.
        
        Args:
            project_id: GCP project ID (if None, uses from environment)
        """
        if not HAS_FIRESTORE:
            raise ImportError("google-cloud-firestore not installed")
        
        try:
            if project_id:
                self.db = firestore.Client(project=project_id)
            else:
                self.db = firestore.Client()
            
            self.project_id = project_id or self.db.project
            logger.info(f"Firestore initialized for project: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            raise
    
    def add_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adds article to Firestore.
        
        Args:
            article_data: Dictionary with fields url, title, summary, key_points, intents, values, etc.
            
        Returns:
            Dictionary with result
        """
        try:
            url = article_data.get("url", "")
            if not url:
                return {"status": "error", "error_message": "URL is required"}
            
            doc_id = url.replace("https://", "").replace("http://", "").replace("/", "_")[:200]
            
            article_ref = self.db.collection("articles").document(doc_id)
            
            article_data["created_at"] = firestore.SERVER_TIMESTAMP
            article_data["updated_at"] = firestore.SERVER_TIMESTAMP
            
            article_ref.set(article_data, merge=True)
            
            logger.info(f"Article added to Firestore: {doc_id}")
            
            return {
                "status": "success",
                "article_id": doc_id,
                "url": url
            }
        except Exception as e:
            logger.error(f"Error adding article to Firestore: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    def add_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Adds entity to graph.
        
        Args:
            entity: Dictionary with fields type, canonical_name, aliases, confidence, article_url
            
        Returns:
            Dictionary with result
        """
        try:
            canonical_name = entity.get("canonical_name", "").strip()
            if not canonical_name:
                return {"status": "error", "error_message": "Empty canonical_name"}
            
            entity_type = entity.get("type", "ENTITY")
            node_id = f"{entity_type}:{canonical_name}"
            article_url = entity.get("article_url")  # Get article_url from entity
            
            entity_ref = self.db.collection("entities").document(node_id)
            
            existing = entity_ref.get()
            
            if existing.exists:
                existing_data = existing.to_dict()
                existing_aliases = set(existing_data.get("aliases", []))
                new_aliases = set(entity.get("aliases", []))
                merged_aliases = list(existing_aliases | new_aliases)
                
                existing_article_urls = existing_data.get("article_urls", [])
                if article_url and article_url not in existing_article_urls:
                    existing_article_urls.append(article_url)
                
                update_data = {
                    "aliases": merged_aliases,
                    "confidence": max(existing_data.get("confidence", 0), entity.get("confidence", 0)),
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
                
                if article_url:
                    update_data["article_urls"] = existing_article_urls
                    if not existing_data.get("article_url"):
                        update_data["article_url"] = article_url
                
                entity_ref.update(update_data)
                
                return {
                    "status": "success",
                    "node_id": node_id,
                    "created": False,
                    "updated": True
                }
            else:
                entity_data = {
                    "type": entity_type,
                    "canonical_name": canonical_name,
                    "aliases": entity.get("aliases", []),
                    "confidence": entity.get("confidence", 0.5),
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
                
                if article_url:
                    entity_data["article_url"] = article_url
                    entity_data["article_urls"] = [article_url]
                
                entity_ref.set(entity_data)
                
                return {
                    "status": "success",
                    "node_id": node_id,
                    "created": True
                }
        except Exception as e:
            logger.error(f"Error adding entity to Firestore: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    def add_relation(self, relation: Dict[str, Any]) -> Dict[str, Any]:
        """Adds relationship to graph.
        
        Args:
            relation: Dictionary with fields subject, predicate, object, confidence, article_url
            
        Returns:
            Dictionary with result
        """
        try:
            subject = relation.get("subject", "").strip()
            predicate = relation.get("predicate", "").strip()
            obj = relation.get("object", "").strip()
            article_url = relation.get("article_url")  # Get article_url from relation
            
            if not all([subject, predicate, obj]):
                return {"status": "error", "error_message": "Missing subject, predicate, or object"}
            
            # Create relationship ID
            edge_id = f"{subject}::{predicate}::{obj}"
            
            relation_ref = self.db.collection("relations").document(edge_id)
            
            # Get existing relationship
            existing = relation_ref.get()
            
            relation_data = {
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "confidence": relation.get("confidence", 0.5),
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            
            if article_url:
                relation_data["article_url"] = article_url
                
                if existing.exists:
                    existing_data = existing.to_dict()
                    existing_article_urls = existing_data.get("article_urls", [])
                    if article_url not in existing_article_urls:
                        existing_article_urls.append(article_url)
                    relation_data["article_urls"] = existing_article_urls
                    relation_data["confidence"] = max(
                        existing_data.get("confidence", 0),
                        relation.get("confidence", 0.5)
                    )
                else:
                    relation_data["article_urls"] = [article_url]
                    relation_data["created_at"] = firestore.SERVER_TIMESTAMP
            
            relation_ref.set(relation_data, merge=True)
            
            return {
                "status": "success",
                "edge_id": edge_id,
                "created": not existing.exists if existing.exists else True
            }
        except Exception as e:
            logger.error(f"Error adding relation to Firestore: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Gets graph statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            logger.info(f"Getting graph stats from Firestore (project: {self.project_id})")
            entities_ref = self.db.collection("entities")
            relations_ref = self.db.collection("relations")
            articles_ref = self.db.collection("articles")
            
            # Count (this can be slow for large collections)
            # In production better to use counters
            logger.info("Counting entities...")
            entities_count = len(list(entities_ref.stream()))
            logger.info(f"Found {entities_count} entities")
            
            logger.info("Counting relations...")
            relations_count = len(list(relations_ref.stream()))
            logger.info(f"Found {relations_count} relations")
            
            logger.info("Counting articles...")
            articles_count = len(list(articles_ref.stream()))
            logger.info(f"Found {articles_count} articles")
            
            # Entity types
            entity_types = defaultdict(int)
            logger.info("Counting entity types...")
            for entity_doc in entities_ref.stream():
                entity_data = entity_doc.to_dict()
                entity_type = entity_data.get("type", "ENTITY")
                entity_types[entity_type] += 1
            
            result = {
                "nodes_count": entities_count,
                "edges_count": relations_count,
                "articles_count": articles_count,
                "entity_types": dict(entity_types)
            }
            logger.info(f"Graph stats result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}", exc_info=True)
            return {
                "nodes_count": 0,
                "edges_count": 0,
                "articles_count": 0,
                "entity_types": {}
            }
    
    def get_snapshot(self, limit: int = 100) -> Dict[str, Any]:
        """Gets graph snapshot.
        
        Args:
            limit: Maximum number of nodes
            
        Returns:
            Dictionary with snapshot
        """
        try:
            entities_ref = self.db.collection("entities")
            
            # Sort by confidence (if index exists)
            # In production better to use composite index
            entities = []
            for entity_doc in entities_ref.stream():
                entity_data = entity_doc.to_dict()
                entity_data["node_id"] = entity_doc.id
                entities.append(entity_data)
            
            # Sort by confidence
            entities.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            entities = entities[:limit]
            
            return {
                "nodes": entities,
                "total_nodes": len(entities),
                "edges_count": len(list(self.db.collection("relations").stream()))
            }
        except Exception as e:
            logger.error(f"Error getting snapshot: {e}")
            return {
                "nodes": [],
                "total_nodes": 0,
                "edges_count": 0
            }
    
    def search_articles_by_topic(self, topic: str, limit: int = 10, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Searches articles by topic with improved relevance search and caching.
        
        Args:
            topic: Topic to search
            limit: Maximum number of results
            use_cache: Use cache
            
        Returns:
            List of articles with relevance
        """
        try:
            from tools.cache import cache_result
            
            # Use cache if enabled
            if use_cache:
                # Create cached function
                @cache_result(ttl=3600)  # Cache for 1 hour
                def _search_impl(search_topic: str, search_limit: int):
                    return self._search_articles_impl(search_topic, search_limit)
                
                return _search_impl(topic, limit)
            else:
                return self._search_articles_impl(topic, limit)
        except Exception as e:
            logger.error(f"Error searching articles: {e}")
            return []
    
    def _search_articles_impl(self, topic: str, limit: int) -> List[Dict[str, Any]]:
        """Internal implementation of article search."""
        try:
            articles_ref = self.db.collection("articles")
            
            results = []
            topic_lower = topic.lower()
            topic_words = set(topic_lower.split())
            
            for article_doc in articles_ref.stream():
                article_data = article_doc.to_dict()
                article_id = article_doc.id
                
                title = article_data.get("title", "").lower()
                summary = article_data.get("summary", "").lower()
                key_points = " ".join(article_data.get("key_points", [])).lower()
                intents = " ".join(article_data.get("intents", [])).lower()
                values = " ".join(article_data.get("values", [])).lower()
                
                relevance_score = 0
                
                # Title - most important (weight 3)
                title_words = set(title.split())
                common_title = topic_words & title_words
                relevance_score += len(common_title) * 3
                
                # Summary (weight 2)
                summary_words = set(summary.split())
                common_summary = topic_words & summary_words
                relevance_score += len(common_summary) * 2
                
                # Key points (weight 2)
                key_points_words = set(key_points.split())
                common_key_points = topic_words & key_points_words
                relevance_score += len(common_key_points) * 2
                
                # Intents and values (weight 1)
                intents_words = set(intents.split())
                values_words = set(values.split())
                common_intents = topic_words & intents_words
                common_values = topic_words & values_words
                relevance_score += len(common_intents) + len(common_values)
                
                # Exact phrase match
                if topic_lower in title:
                    relevance_score += 5
                if topic_lower in summary:
                    relevance_score += 3
                
                if relevance_score > 0:
                    article_data["article_id"] = article_id
                    article_data["relevance_score"] = relevance_score
                    results.append(article_data)
            
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return results[:limit]
        except Exception as e:
            logger.error(f"Error searching articles: {e}")
            return []
    
    def get_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Gets article by URL.
        
        Args:
            url: Article URL
            
        Returns:
            Dictionary with article data or None
        """
        try:
            doc_id = url.replace("https://", "").replace("http://", "").replace("/", "_")[:200]
            article_ref = self.db.collection("articles").document(doc_id)
            article_doc = article_ref.get()
            
            if article_doc.exists:
                data = article_doc.to_dict()
                data["article_id"] = doc_id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting article: {e}")
            return None
    
    def find_related_articles(self, article_url: str, limit: int = 5, use_embeddings: bool = True) -> List[Dict[str, Any]]:
        """Finds related articles using knowledge graph with embeddings.
        
        Args:
            article_url: Source article URL
            limit: Maximum number of related articles
            use_embeddings: Use embeddings for semantic search
            
        Returns:
            List of related articles with similarity score
        """
        try:
            from tools.embeddings import generate_embedding_single
            from tools.cache import cache_result
            import numpy as np
            
            # Get article
            article = self.get_article(article_url)
            if not article:
                return []
            
            # Extract text for search
            key_points = " ".join(article.get("key_points", []))
            intents = " ".join(article.get("intents", []))
            values = " ".join(article.get("values", []))
            search_text = f"{key_points} {intents} {values}"
            
            articles_ref = self.db.collection("articles")
            related = []
            
            if use_embeddings:
                source_embedding_result = generate_embedding_single(search_text)
                if source_embedding_result.get("status") != "success":
                    logger.warning("Failed to generate embedding, falling back to keyword search")
                    use_embeddings = False
                else:
                    source_embedding = np.array(source_embedding_result["embedding"])
            
            all_articles = []
            for article_doc in articles_ref.stream():
                article_data = article_doc.to_dict()
                article_id = article_doc.id
                
                # Skip the article itself
                if article_data.get("url") == article_url:
                    continue
                
                all_articles.append((article_id, article_data))
            
            if use_embeddings:
                for article_id, article_data in all_articles:
                    other_key_points = " ".join(article_data.get("key_points", []))
                    other_intents = " ".join(article_data.get("intents", []))
                    other_values = " ".join(article_data.get("values", []))
                    other_text = f"{other_key_points} {other_intents} {other_values}"
                    
                    other_embedding_result = generate_embedding_single(other_text)
                    if other_embedding_result.get("status") == "success":
                        other_embedding = np.array(other_embedding_result["embedding"])
                        
                        # Cosine similarity
                        similarity = np.dot(source_embedding, other_embedding) / (
                            np.linalg.norm(source_embedding) * np.linalg.norm(other_embedding)
                        )
                        
                        if similarity > 0.3:  # Similarity threshold
                            article_data["article_id"] = article_id
                            article_data["similarity"] = float(similarity)
                            related.append(article_data)
            else:
                # Fallback: keyword-based search
                search_words = set(search_text.lower().split())
                
                for article_id, article_data in all_articles:
                    other_key_points = " ".join(article_data.get("key_points", [])).lower()
                    other_intents = " ".join(article_data.get("intents", [])).lower()
                    other_values = " ".join(article_data.get("values", [])).lower()
                    other_text = f"{other_key_points} {other_intents} {other_values}"
                    other_words = set(other_text.split())
                    
                    common_words = search_words & other_words
                    if len(common_words) >= 2:
                        article_data["article_id"] = article_id
                        article_data["common_words"] = len(common_words)
                        article_data["similarity"] = len(common_words) / max(len(search_words), 1)
                        related.append(article_data)
            
            # Sort by similarity
            related.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            
            return related[:limit]
        except Exception as e:
            logger.error(f"Error finding related articles: {e}", exc_info=True)
            return []


"""Unit tests for Firestore Knowledge Graph"""

import pytest
from storage.firestore_kg import FirestoreKnowledgeGraph


class TestFirestoreKG:
    """Tests for Firestore Knowledge Graph"""
    
    def test_add_entity(self):
        """Test entity addition"""
        # Use in-memory for tests or mock
        # In real tests can use test Firestore database
        kg = FirestoreKnowledgeGraph()
        
        entity = {
            "type": "CONCEPT",
            "canonical_name": "Microservices",
            "aliases": ["MSA", "Microservices"],
            "confidence": 0.9
        }
        
        result = kg.add_entity(entity)
        
        assert result is not None
        assert result.get("status") == "success"
        assert "node_id" in result
    
    def test_add_relation(self):
        """Test relation addition"""
        kg = FirestoreKnowledgeGraph()
        
        relation = {
            "subject": "Microservices",
            "predicate": "uses",
            "object": "Docker",
            "confidence": 0.8
        }
        
        result = kg.add_relation(relation)
        
        assert result is not None
        assert result.get("status") == "success"
        assert "edge_id" in result
    
    def test_get_graph_stats(self):
        """Test graph statistics retrieval"""
        kg = FirestoreKnowledgeGraph()
        
        stats = kg.get_graph_stats()
        
        assert stats is not None
        assert "nodes_count" in stats
        assert "edges_count" in stats
        assert "articles_count" in stats
        assert isinstance(stats["nodes_count"], int)
        assert isinstance(stats["edges_count"], int)
    
    def test_search_articles_by_topic(self):
        """Test article search by topic"""
        kg = FirestoreKnowledgeGraph()
        
        results = kg.search_articles_by_topic("microservices", limit=5)
        
        assert isinstance(results, list)
        # If there are results, check structure
        if len(results) > 0:
            article = results[0]
            assert "title" in article
            assert "url" in article
            assert "relevance_score" in article


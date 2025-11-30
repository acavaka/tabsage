"""
Knowledge Graph client - unified interface for working with knowledge graph

This module provides a unified interface for working with knowledge graph,
allowing switching between different implementations (InMemory, Firestore, Neo4j, etc.)
without changing agent code.

Architecture:
- Factory pattern for creating graph instances
- Support for multiple providers via KG_PROVIDER environment variable
- Automatic fallback to InMemory if production provider unavailable
- Global instances for reuse

Supported providers:
- inmemory: InMemoryKnowledgeGraph (for development and tests)
- firestore: FirestoreKnowledgeGraph (production, persistent storage)
- neo4j: Neo4jKnowledgeGraph (TODO: for large graphs)
- neptune: NeptuneKnowledgeGraph (TODO: for AWS environment)
- pgvector: PgVectorKnowledgeGraph (TODO: for vector search)

Usage:
    from tools.kg_client import get_kg_instance
    
    kg = get_kg_instance()
    await kg.add_entity({"type": "CONCEPT", "canonical_name": "AI"})
    stats = await kg.get_graph_stats()
"""

import os
from typing import List, Dict, Any, Optional, Set
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Production KG providers
KG_PROVIDER = os.getenv("KG_PROVIDER", "inmemory")  # inmemory, firestore, neo4j, neptune, pgvector


class InMemoryKnowledgeGraph:
    """In-memory knowledge graph implementation for development and testing.
    
    In production will be replaced with Neo4j, Neptune or pgVector.
    """
    
    def __init__(self):
        """Initialize empty graph"""
        self.nodes: Dict[str, Dict[str, Any]] = {}  # node_id -> node_data
        self.edges: List[Dict[str, Any]] = []  # List of edge dicts
        self.node_index: Dict[str, Set[str]] = defaultdict(set)  # canonical_name -> {node_ids}
    
    def add_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Adds entity to graph.
        
        Args:
            entity: Dictionary with fields type, canonical_name, aliases, confidence
            
        Returns:
            Dictionary with result
            Success: {"status": "success", "node_id": "...", "created": True/False}
            Error: {"status": "error", "error_message": "..."}
        """
        try:
            canonical_name = entity.get("canonical_name", "").strip()
            if not canonical_name:
                return {
                    "status": "error",
                    "error_message": "Empty canonical_name"
                }
            
            node_id = f"{entity.get('type', 'ENTITY')}:{canonical_name}"
            
            if node_id in self.nodes:
                existing = self.nodes[node_id]
                existing["aliases"] = list(set(existing.get("aliases", []) + entity.get("aliases", [])))
                existing["confidence"] = max(existing.get("confidence", 0), entity.get("confidence", 0))
                return {
                    "status": "success",
                    "node_id": node_id,
                    "created": False,
                    "updated": True
                }
            else:
                self.nodes[node_id] = {
                    "type": entity.get("type", "ENTITY"),
                    "canonical_name": canonical_name,
                    "aliases": entity.get("aliases", []),
                    "confidence": entity.get("confidence", 0.5)
                }
                self.node_index[canonical_name.lower()].add(node_id)
                return {
                    "status": "success",
                    "node_id": node_id,
                    "created": True
                }
        except Exception as e:
            logger.error(f"Error adding entity: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    def add_relation(self, relation: Dict[str, Any]) -> Dict[str, Any]:
        """Adds relationship to graph.
        
        Args:
            relation: Dictionary with fields subject, predicate, object, confidence
            
        Returns:
            Dictionary with result
            Success: {"status": "success", "edge_id": "...", "created": True/False}
            Error: {"status": "error", "error_message": "..."}
        """
        try:
            subject = relation.get("subject", "").strip()
            predicate = relation.get("predicate", "").strip()
            obj = relation.get("object", "").strip()
            
            if not all([subject, predicate, obj]):
                return {
                    "status": "error",
                    "error_message": "Missing subject, predicate, or object"
                }
            
            subject_id = self._find_node_id(subject)
            object_id = self._find_node_id(obj)
            
            if not subject_id or not object_id:
                return {
                    "status": "error",
                    "error_message": f"Nodes not found: subject={subject}, object={obj}"
                }
            
            edge_id = f"{subject_id}--{predicate}--{object_id}"
            existing_edge = next(
                (e for e in self.edges if e.get("edge_id") == edge_id),
                None
            )
            
            if existing_edge:
                existing_edge["confidence"] = max(
                    existing_edge.get("confidence", 0),
                    relation.get("confidence", 0)
                )
                return {
                    "status": "success",
                    "edge_id": edge_id,
                    "created": False,
                    "updated": True
                }
            else:
                edge = {
                    "edge_id": edge_id,
                    "subject_id": subject_id,
                    "subject": subject,
                    "predicate": predicate,
                    "object_id": object_id,
                    "object": obj,
                    "confidence": relation.get("confidence", 0.5)
                }
                self.edges.append(edge)
                return {
                    "status": "success",
                    "edge_id": edge_id,
                    "created": True
                }
        except Exception as e:
            logger.error(f"Error adding relation: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    def _find_node_id(self, canonical_name: str) -> Optional[str]:
        """Finds node_id by canonical_name.
        
        Args:
            canonical_name: Entity name
            
        Returns:
            node_id or None
        """
        normalized = canonical_name.lower()
        matching_ids = self.node_index.get(normalized, set())
        if matching_ids:
            return list(matching_ids)[0]  # Return first found
        
        # Search by exact match in nodes
        for node_id, node_data in self.nodes.items():
            if node_data.get("canonical_name", "").lower() == normalized:
                return node_id
            if normalized in [a.lower() for a in node_data.get("aliases", [])]:
                return node_id
        
        return None
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Returns graph statistics.
        
        Returns:
            Dictionary with statistics
        """
        entity_types = defaultdict(int)
        for node in self.nodes.values():
            entity_types[node.get("type", "UNKNOWN")] += 1
        
        return {
            "nodes_count": len(self.nodes),
            "edges_count": len(self.edges),
            "entity_types": dict(entity_types)
        }
    
    def get_snapshot(self, limit: int = 100) -> Dict[str, Any]:
        """Returns graph snapshot for Topic Discovery.
        
        Args:
            limit: Maximum number of nodes to return
            
        Returns:
            Dictionary with graph snapshot
        """
        # Sort nodes by confidence
        sorted_nodes = sorted(
            self.nodes.items(),
            key=lambda x: x[1].get("confidence", 0),
            reverse=True
        )[:limit]
        
        return {
            "nodes": [
                {
                    "node_id": node_id,
                    **node_data
                }
                for node_id, node_data in sorted_nodes
            ],
            "edges_count": len(self.edges),
            "total_nodes": len(self.nodes)
        }


# Global instance for simplicity (in production will be via dependency injection)
_global_kg: Optional[InMemoryKnowledgeGraph] = None


def get_kg_instance():
    """Gets knowledge graph instance (in-memory or production).
    
    Returns:
        InMemoryKnowledgeGraph, FirestoreKnowledgeGraph or production implementation
    """
    global _global_kg
    
    logger.info(f"Getting KG instance. KG_PROVIDER={KG_PROVIDER}, os.getenv('KG_PROVIDER')={os.getenv('KG_PROVIDER')}")
    
    if KG_PROVIDER == "firestore":
        logger.info("Using Firestore provider")
        return _get_firestore_kg()
    elif KG_PROVIDER == "neo4j":
        logger.info("Using Neo4j provider")
        return _get_neo4j_kg()
    elif KG_PROVIDER == "neptune":
        logger.info("Using Neptune provider")
        return _get_neptune_kg()
    elif KG_PROVIDER == "pgvector":
        logger.info("Using PgVector provider")
        return _get_pgvector_kg()
    else:
        # In-memory for development
        logger.warning(f"Using InMemory provider (KG_PROVIDER={KG_PROVIDER})")
        if _global_kg is None:
            _global_kg = InMemoryKnowledgeGraph()
        return _global_kg


def _get_firestore_kg():
    """Gets Firestore knowledge graph.
    
    Returns:
        FirestoreKnowledgeGraph
    """
    global _global_kg
    
    try:
        logger.info("Importing FirestoreKnowledgeGraph...")
        from storage.firestore_kg import FirestoreKnowledgeGraph
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        logger.info(f"Initializing Firestore with project_id={project_id}")
        kg = FirestoreKnowledgeGraph(project_id=project_id)
        logger.info(f"Firestore initialized successfully: {type(kg)}")
        return kg
    except ImportError as e:
        logger.error(f"Firestore not available (ImportError): {e}, falling back to in-memory", exc_info=True)
        if _global_kg is None:
            _global_kg = InMemoryKnowledgeGraph()
        return _global_kg
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}, falling back to in-memory", exc_info=True)
        if _global_kg is None:
            _global_kg = InMemoryKnowledgeGraph()
        return _global_kg


def _get_neo4j_kg():
    """Gets Neo4j knowledge graph.
    
    TODO: Implement Neo4j integration
    Example:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    # ... create Neo4jKnowledgeGraph class ...
    """
    logger.warning("Neo4j integration not implemented, falling back to in-memory")
    global _global_kg
    if _global_kg is None:
        _global_kg = InMemoryKnowledgeGraph()
    return _global_kg


def _get_neptune_kg():
    """Gets Amazon Neptune knowledge graph.
    
    TODO: Implement Amazon Neptune integration
    Example:
    from gremlin_python.driver import client, serializer
    # ... create NeptuneKnowledgeGraph class ...
    """
    logger.warning("Neptune integration not implemented, falling back to in-memory")
    global _global_kg
    if _global_kg is None:
        _global_kg = InMemoryKnowledgeGraph()
    return _global_kg


def _get_pgvector_kg():
    """Gets pgVector knowledge graph.
    
    TODO: Implement pgVector + PostgreSQL integration
    Example:
    import psycopg2
    from pgvector.psycopg2 import register_vector
    # ... create PgVectorKnowledgeGraph class ...
    """
    logger.warning("pgVector integration not implemented, falling back to in-memory")
    global _global_kg
    if _global_kg is None:
        _global_kg = InMemoryKnowledgeGraph()
    return _global_kg


def reset_kg_instance():
    """Resets graph (for tests)."""
    global _global_kg
    _global_kg = InMemoryKnowledgeGraph()


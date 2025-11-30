"""NER (Named Entity Recognition) and Entity Linking tools"""

import re
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def extract_entities_simple(text: str) -> Dict[str, Any]:
    """Simple entity extraction via patterns (stub).
    
    In production, LLM or specialized NER model will be used here.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with results
        Success: {"status": "success", "entities": [...]}
        Error: {"status": "error", "error_message": "..."}
    """
    if not text:
        return {
            "status": "error",
            "error_message": "Empty text"
        }
    
    entities = []
    
    # Simple patterns for demonstration
    # In production, LLM will do this
    
    # Organizations (capitalized words + Inc, Corp, Ltd, etc.)
    org_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Corp|Ltd|LLC|Company|Corporation))?)\b'
    orgs = re.findall(org_pattern, text)
    for org in set(orgs):
        if len(org) > 2:  # Filter short matches
            entities.append({
                "type": "ORGANIZATION",
                "canonical_name": org,
                "aliases": [],
                "confidence": 0.6  # Low confidence for simple patterns
            })
    
    # Locations (can be extended)
    location_keywords = ["city", "country", "university", "institute"]
    # In production, more complex logic will be used
    
    return {
        "status": "success",
        "entities": entities
    }


def link_entities(entities: List[Dict[str, Any]], knowledge_base: Optional[Dict] = None) -> Dict[str, Any]:
    """Links extracted entities with knowledge base (entity linking).
    
    Args:
        entities: List of extracted entities
        knowledge_base: Knowledge base for linking (optional)
        
    Returns:
        Dictionary with results
        Success: {"status": "success", "linked_entities": [...]}
        Error: {"status": "error", "error_message": "..."}
    """
    if not entities:
        return {
            "status": "error",
            "error_message": "Empty entities list"
        }
    
    linked_entities = []
    
    # Simple logic: name normalization and duplicate search
    # In production, real entity linking with knowledge base will be here
    seen_names = {}
    
    for entity in entities:
        canonical = entity.get("canonical_name", "").strip()
        if not canonical:
            continue
        
        # Normalization: lowercase for comparison
        normalized = canonical.lower()
        
        if normalized in seen_names:
            # Duplicate found - add as alias
            existing = seen_names[normalized]
            if canonical not in existing.get("aliases", []):
                existing["aliases"].append(canonical)
        else:
            # New entity
            linked_entity = {
                "type": entity.get("type", "UNKNOWN"),
                "canonical_name": canonical,
                "aliases": entity.get("aliases", []).copy(),
                "confidence": entity.get("confidence", 0.5)
            }
            linked_entities.append(linked_entity)
            seen_names[normalized] = linked_entity
    
    return {
        "status": "success",
        "linked_entities": linked_entities
    }


def normalize_entity_name(name: str) -> str:
    """Normalizes entity name.
    
    Args:
        name: Original name
        
    Returns:
        Normalized name
    """
    # Remove extra spaces, convert to standard form
    normalized = " ".join(name.split())
    return normalized.strip()


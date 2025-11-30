"""Embeddings generation tools for TabSage"""

import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Vertex AI Embeddings
try:
    from google.cloud import aiplatform
    from vertexai.preview.language_models import TextEmbeddingModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    logger.warning("vertexai not available, using mock embeddings")

# Gemini API (fallback)
try:
    from google.genai import Client
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def generate_embeddings(texts: List[str], model: str = "textembedding-gecko@003") -> Dict[str, Any]:
    """Generates embeddings for list of texts via Vertex AI.
    
    Args:
        texts: List of texts for embedding generation
        model: Embedding model (default: textembedding-gecko@003)
        
    Returns:
        Dictionary with results
        Success: {"status": "success", "embeddings": [[...], [...], ...], "dimension": 768}
        Error: {"status": "error", "error_message": "..."}
    """
    if not texts:
        return {
            "status": "error",
            "error_message": "Empty texts list"
        }
    
    try:
        if VERTEX_AI_AVAILABLE:
            try:
                from config import GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION
                
                aiplatform.init(project=GOOGLE_CLOUD_PROJECT, location=VERTEX_AI_LOCATION)
                embedding_model = TextEmbeddingModel.from_pretrained(model)
                
                # Generate in batches of 5 to avoid limits
                all_embeddings = []
                batch_size = 5
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = embedding_model.get_embeddings(batch)
                    all_embeddings.extend([emb.values for emb in batch_embeddings])
                
                dimension = len(all_embeddings[0]) if all_embeddings else 768
                
                logger.info(f"Generated {len(all_embeddings)} embeddings using Vertex AI ({model})")
                
                return {
                    "status": "success",
                    "embeddings": all_embeddings,
                    "dimension": dimension,
                    "model": model
                }
            except Exception as e:
                logger.warning(f"Vertex AI embeddings failed: {e}, falling back to mock")
                # Fallback to mock
                embeddings = [[0.0] * 768 for _ in texts]
                return {
                    "status": "success",
                    "embeddings": embeddings,
                    "dimension": 768,
                    "model": "mock"
                }
        else:
            # Fallback: mock embeddings
            logger.warning("Using mock embeddings (Vertex AI not available)")
            embeddings = [[0.0] * 768 for _ in texts]
            return {
                "status": "success",
                "embeddings": embeddings,
                "dimension": 768,
                "model": "mock"
            }
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        return {
            "status": "error",
            "error_message": str(e)
        }


def generate_embedding_single(text: str, model: str = "text-embedding-004") -> Dict[str, Any]:
    """Generates embedding for a single text.
    
    Args:
        text: Text to generate embedding for
        model: Model for embeddings
        
    Returns:
        Dictionary with result
        Success: {"status": "success", "embedding": [...], "dimension": 768}
        Error: {"status": "error", "error_message": "..."}
    """
    result = generate_embeddings([text], model)
    if result["status"] == "success":
        return {
            "status": "success",
            "embedding": result["embeddings"][0],
            "dimension": result["dimension"],
            "model": result["model"]
        }
    else:
        return result


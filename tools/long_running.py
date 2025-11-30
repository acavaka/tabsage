"""
Long-Running Operations - operations with pause for confirmation

Based on Day 2b: Tools Best Practices
Implements long-running operations pattern with human-in-the-loop.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

try:
    from google.adk.tools import ToolContext
    HAS_ADK_TOOLS = True
except ImportError:
    HAS_ADK_TOOLS = False
    ToolContext = object

from observability.logging import get_logger

logger = get_logger(__name__)


class OperationStatus(Enum):
    """Long-running operation status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


def process_large_article_batch(
    urls: list[str],
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    Processes large article batch with confirmation.
    
    If articles exceed threshold, requests user confirmation.
    
    Args:
        urls: List of article URLs to process
        tool_context: Tool context (for confirmation request)
        
    Returns:
        Dictionary with operation result
    """
    BATCH_THRESHOLD = 10
    
    if len(urls) > BATCH_THRESHOLD:
        # Request confirmation
        if tool_context and HAS_ADK_TOOLS:
            confirmation_message = (
                f"You are about to process {len(urls)} articles. "
                f"This may take significant time and use many resources. "
                f"Continue?"
            )
            
            approved = tool_context.request_confirmation(confirmation_message)
            
            if not approved:
                logger.info("Large batch processing cancelled by user", extra={
                    "event_type": "batch_processing_cancelled",
                    "urls_count": len(urls)
                })
                return {
                    "status": "cancelled",
                    "message": "Processing cancelled by user"
                }
        
        logger.info(f"Large batch processing approved: {len(urls)} URLs", extra={
            "event_type": "batch_processing_approved",
            "urls_count": len(urls)
        })
    
    results = []
    for url in urls:
        results.append({
            "url": url,
            "status": "processed"
        })
    
    return {
        "status": "completed",
        "processed_count": len(results),
        "results": results
    }


def delete_article_from_kg(
    article_id: str,
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    Deletes article from knowledge graph with confirmation.
    
    This is an irreversible operation, so always requests confirmation.
    
    Args:
        article_id: Article ID to delete
        tool_context: Tool context
        
    Returns:
        Dictionary with result
    """
    if tool_context and HAS_ADK_TOOLS:
        confirmation_message = (
            f"You are about to delete article {article_id} from the knowledge graph. "
            f"This action is irreversible. Continue?"
        )
        
        approved = tool_context.request_confirmation(confirmation_message)
        
        if not approved:
            logger.info(f"Article deletion cancelled: {article_id}", extra={
                "event_type": "article_deletion_cancelled",
                "article_id": article_id
            })
            return {
                "status": "cancelled",
                "message": "Deletion cancelled by user"
            }
    
    logger.warning(f"Article deleted from KG: {article_id}", extra={
        "event_type": "article_deleted",
        "article_id": article_id
    })
    
    return {
        "status": "deleted",
        "article_id": article_id
    }


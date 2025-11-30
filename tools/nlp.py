"""NLP tools for text processing: tokenization, chunking, text cleaning"""

import re
from typing import List, Dict, Any


def clean_text(text: str) -> str:
    """Remove ads, markers, and normalize whitespace.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text without ads and markers
    """
    text = re.sub(r'\[.*?ad.*?\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?ad.*?\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<.*?ad.*?>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def chunk_text(
    text: str, 
    max_chunks: int = 5, 
    chunk_size: int = 1000, 
    overlap: int = 200
) -> Dict[str, Any]:
    """Split text into chunks.
    
    Args:
        text: Text to chunk
        max_chunks: Maximum number of chunks (default: 5)
        chunk_size: Target size of each chunk in characters (default: 1000)
        overlap: Overlap between chunks in characters (default: 200)
        
    Returns:
        Dictionary with status and chunks list
        Success: {"status": "success", "chunks": [...]}
        Error: {"status": "error", "error_message": "..."}
    """
    if not text or len(text.strip()) == 0:
        return {
            "status": "error",
            "error_message": "Empty text provided"
        }
    
    cleaned = clean_text(text)
    
    if len(cleaned) <= chunk_size:
        return {
            "status": "success",
            "chunks": [cleaned]
        }
    
    sentences = re.split(r'[.!?]\s+', cleaned)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if current_chunk and len(current_chunk) + len(sentence) + 1 > chunk_size:
            chunks.append(current_chunk)
            current_chunk = ""
            
            if len(chunks) >= max_chunks:
                break
        
        if current_chunk:
            current_chunk += ". " + sentence
        else:
            current_chunk = sentence
    
    if current_chunk and len(chunks) < max_chunks:
        chunks.append(current_chunk)
    
    if len(chunks) > max_chunks:
        merged = " ".join(chunks[max_chunks-1:])
        chunks = chunks[:max_chunks-1] + [merged]
    
    return {
        "status": "success",
        "chunks": chunks
    }


def detect_language(text: str) -> str:
    """Detect language of text (simple heuristic).
    
    Args:
        text: Text to analyze
        
    Returns:
        Language code ('ru', 'en', or 'unknown')
    """
    cyrillic_count = len(re.findall(r'[а-яёА-ЯЁ]', text))
    latin_count = len(re.findall(r'[a-zA-Z]', text))
    
    if cyrillic_count > latin_count * 0.5:
        return "ru"
    elif latin_count > 0:
        return "en"
    else:
        return "unknown"


"""Pytest configuration and fixtures"""

import pytest
import os
import sys
from unittest.mock import Mock, patch

# Add path to modules

@pytest.fixture
def mock_gemini():
    """Mock for Gemini API"""
    with patch('tabsage.config.GEMINI_API_KEY', 'test-key'):
        yield

@pytest.fixture
def sample_text():
    """Sample text for testing"""
    return """
    Microservices architecture is an approach to application development,
    where an application is broken down into small independent services.
    Each service is responsible for a specific business function and can be
    deployed independently. This allows teams to work in parallel
    and scale individual components as needed.
    """

@pytest.fixture
def sample_article_data():
    """Sample article data"""
    return {
        "url": "https://habr.com/ru/articles/519982/",
        "title": "Microservices Architecture",
        "text": "Microservices architecture is an approach to development...",
        "key_points": ["Microservices", "Independent services", "Scaling"],
        "intents": ["Learning architecture", "Applying in projects"],
        "values": ["Flexibility", "Scalability"]
    }

@pytest.fixture
def mock_kg():
    """Mock for Knowledge Graph"""
    from tools.kg_client import InMemoryKnowledgeGraph
    return InMemoryKnowledgeGraph()


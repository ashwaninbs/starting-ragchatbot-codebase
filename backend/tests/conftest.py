"""Shared fixtures for RAG system tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_rag_system():
    """A fully mocked RAGSystem for use in API tests."""
    rag = MagicMock()

    # Mock session_manager.create_session
    rag.session_manager.create_session.return_value = "session_1"

    # Mock query to return a standard response
    rag.query.return_value = (
        "Python is a programming language.",
        ["Course: Intro to Python"],
    )

    # Mock get_course_analytics
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Intro to Python", "Advanced ML"],
    }

    return rag


@pytest.fixture
def sample_query_payload():
    """Standard query request payload."""
    return {"query": "What is Python?"}


@pytest.fixture
def sample_query_payload_with_session():
    """Query request payload with an existing session."""
    return {"query": "Tell me more", "session_id": "session_1"}

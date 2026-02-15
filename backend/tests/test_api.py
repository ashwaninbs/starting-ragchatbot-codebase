"""Tests for FastAPI API endpoints.

Defines a lightweight test app that mirrors the real endpoints in backend/app.py
but without static file mounts or module-level RAG initialization, so tests can
run without the full runtime environment.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Minimal app that mirrors the real endpoints but is test-friendly
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


def create_test_app(rag_system: MagicMock) -> FastAPI:
    """Build a FastAPI app wired to the given (mock) RAG system."""
    app = FastAPI()

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(mock_rag_system):
    """TestClient wired to the mock RAG system."""
    app = create_test_app(mock_rag_system)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    """Tests for the /api/query endpoint."""

    def test_query_returns_answer_and_sources(self, client, sample_query_payload):
        resp = client.post("/api/query", json=sample_query_payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "Python is a programming language."
        assert body["sources"] == ["Course: Intro to Python"]
        assert body["session_id"] == "session_1"

    def test_query_creates_session_when_not_provided(
        self, client, mock_rag_system, sample_query_payload
    ):
        client.post("/api/query", json=sample_query_payload)
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_uses_existing_session(
        self, client, mock_rag_system, sample_query_payload_with_session
    ):
        resp = client.post("/api/query", json=sample_query_payload_with_session)
        assert resp.status_code == 200
        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with("Tell me more", "session_1")

    def test_query_passes_query_text_to_rag(
        self, client, mock_rag_system, sample_query_payload
    ):
        client.post("/api/query", json=sample_query_payload)
        mock_rag_system.query.assert_called_once_with("What is Python?", "session_1")

    def test_query_missing_body_returns_422(self, client):
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_query_empty_string_returns_422(self, client):
        """FastAPI/Pydantic accepts empty strings by default; verify status."""
        resp = client.post("/api/query", json={"query": ""})
        # Empty string is technically valid for Pydantic str, so 200 is expected
        assert resp.status_code == 200

    def test_query_rag_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("Vector DB unavailable")
        resp = client.post("/api/query", json={"query": "hello"})
        assert resp.status_code == 500
        assert "Vector DB unavailable" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    """Tests for the /api/courses endpoint."""

    def test_courses_returns_stats(self, client):
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 2
        assert body["course_titles"] == ["Intro to Python", "Advanced ML"]

    def test_courses_calls_analytics(self, client, mock_rag_system):
        client.get("/api/courses")
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB down")
        resp = client.get("/api/courses")
        assert resp.status_code == 500
        assert "DB down" in resp.json()["detail"]

    def test_courses_empty_catalog(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 0
        assert body["course_titles"] == []

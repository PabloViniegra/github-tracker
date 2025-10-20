"""
Simplified unit tests for activity routes focusing on search functionality.

These tests focus on the core search/filter functionality without complex mocking.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status

from app.routes.activity import filter_repositories


# =============================================================================
# Filter Repositories Function Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.activity
class TestFilterRepositories:
    """Test the filter_repositories helper function - this is the main search logic."""

    def test_filter_repositories_no_query_returns_all(self):
        """Test that no query parameter returns all repositories."""
        repos = [
            {"name": "repo1", "description": "First repo", "language": "Python"},
            {"name": "repo2", "description": "Second repo", "language": "JavaScript"}
        ]

        result = filter_repositories(repos, None)

        assert len(result) == 2
        assert result == repos

    def test_filter_repositories_empty_query_returns_all(self):
        """Test that empty string query returns all repositories."""
        repos = [
            {"name": "repo1", "description": "First repo", "language": "Python"},
            {"name": "repo2", "description": "Second repo", "language": "JavaScript"}
        ]

        result = filter_repositories(repos, "")

        assert len(result) == 2
        assert result == repos

    def test_filter_repositories_whitespace_query_returns_all(self):
        """Test that whitespace-only query returns all repositories."""
        repos = [
            {"name": "repo1", "description": "First repo", "language": "Python"},
            {"name": "repo2", "description": "Second repo", "language": "JavaScript"}
        ]

        result = filter_repositories(repos, "   ")

        assert len(result) == 2
        assert result == repos

    def test_filter_repositories_by_name(self):
        """Test searching repositories by name."""
        repos = [
            {"name": "fastapi-app", "description": "API project", "language": "Python"},
            {"name": "django-app", "description": "Web project", "language": "Python"},
            {"name": "react-app", "description": "Frontend", "language": "JavaScript"}
        ]

        result = filter_repositories(repos, "fastapi")

        assert len(result) == 1
        assert result[0]["name"] == "fastapi-app"

    def test_filter_repositories_by_description(self):
        """Test searching repositories by description."""
        repos = [
            {"name": "repo1", "description": "Machine learning project", "language": "Python"},
            {"name": "repo2", "description": "Web development", "language": "JavaScript"},
            {"name": "repo3", "description": "Data science project", "language": "Python"}
        ]

        result = filter_repositories(repos, "machine learning")

        assert len(result) == 1
        assert result[0]["name"] == "repo1"

    def test_filter_repositories_by_language(self):
        """Test searching repositories by programming language."""
        repos = [
            {"name": "repo1", "description": "API", "language": "Python"},
            {"name": "repo2", "description": "API", "language": "JavaScript"},
            {"name": "repo3", "description": "API", "language": "Python"}
        ]

        result = filter_repositories(repos, "python")

        assert len(result) == 2
        assert all(r["language"] == "Python" for r in result)

    def test_filter_repositories_by_owner(self):
        """Test searching repositories by owner login."""
        repos = [
            {
                "name": "repo1",
                "description": "Test",
                "owner": {"login": "testuser"}
            },
            {
                "name": "repo2",
                "description": "Test",
                "owner": {"login": "anotheruser"}
            }
        ]

        result = filter_repositories(repos, "testuser")

        assert len(result) == 1
        assert result[0]["owner"]["login"] == "testuser"

    def test_filter_repositories_by_topics(self):
        """Test searching repositories by topics/tags."""
        repos = [
            {
                "name": "repo1",
                "description": "Test",
                "topics": ["python", "machine-learning", "ai"]
            },
            {
                "name": "repo2",
                "description": "Test",
                "topics": ["javascript", "web", "frontend"]
            },
            {
                "name": "repo3",
                "description": "Test",
                "topics": ["python", "web", "backend"]
            }
        ]

        result = filter_repositories(repos, "machine-learning")

        assert len(result) == 1
        assert result[0]["name"] == "repo1"

    def test_filter_repositories_case_insensitive(self):
        """Test that search is case-insensitive."""
        repos = [
            {"name": "FastAPI-Project", "description": "API", "language": "Python"},
            {"name": "django-app", "description": "Web", "language": "python"}
        ]

        # Test uppercase query
        result_upper = filter_repositories(repos, "FASTAPI")
        assert len(result_upper) == 1
        assert result_upper[0]["name"] == "FastAPI-Project"

        # Test lowercase query
        result_lower = filter_repositories(repos, "python")
        assert len(result_lower) == 2

        # Test mixed case query
        result_mixed = filter_repositories(repos, "FaStApI")
        assert len(result_mixed) == 1

    def test_filter_repositories_partial_match(self):
        """Test that search performs partial matching."""
        repos = [
            {"name": "my-fastapi-project", "description": "API", "language": "Python"},
            {"name": "another-repo", "description": "Fast API implementation", "language": "Python"}
        ]

        result = filter_repositories(repos, "fast")

        assert len(result) == 2
        assert all("fast" in r["name"].lower() or "fast" in r["description"].lower() for r in result)

    def test_filter_repositories_multiple_field_matches(self):
        """Test that a query matching multiple fields returns the repository."""
        repos = [
            {
                "name": "python-api",
                "description": "A Python REST API",
                "language": "Python",
                "topics": ["python", "api"]
            }
        ]

        # Should match on name
        result = filter_repositories(repos, "python")
        assert len(result) == 1

        # Should match on description
        result = filter_repositories(repos, "REST")
        assert len(result) == 1

        # Should match on language
        result = filter_repositories(repos, "Python")
        assert len(result) == 1

        # Should match on topics
        result = filter_repositories(repos, "api")
        assert len(result) == 1

    def test_filter_repositories_no_matches(self):
        """Test that search returns empty list when no matches found."""
        repos = [
            {"name": "repo1", "description": "Test", "language": "Python"},
            {"name": "repo2", "description": "Test", "language": "JavaScript"}
        ]

        result = filter_repositories(repos, "nonexistent")

        assert len(result) == 0
        assert result == []

    def test_filter_repositories_with_null_fields(self):
        """Test that search handles None/null fields gracefully."""
        repos = [
            {"name": "repo1", "description": None, "language": "Python"},
            {"name": "repo2", "description": "Test", "language": None},
            {"name": "repo3", "description": None, "language": None}
        ]

        # Should not crash and should handle None gracefully
        result = filter_repositories(repos, "python")
        assert len(result) == 1
        assert result[0]["name"] == "repo1"

    def test_filter_repositories_with_missing_fields(self):
        """Test that search handles missing fields gracefully."""
        repos = [
            {"name": "repo1"},
            {"name": "repo2", "description": "Has description"},
            {"name": "repo3", "language": "Python"}
        ]

        # Should not crash and should handle missing fields
        result = filter_repositories(repos, "python")
        assert len(result) == 1
        assert result[0]["name"] == "repo3"

    def test_filter_repositories_with_empty_topics(self):
        """Test that search handles empty topics list."""
        repos = [
            {"name": "repo1", "topics": []},
            {"name": "repo2", "topics": ["python"]},
            {"name": "repo3", "topics": None}
        ]

        result = filter_repositories(repos, "python")
        assert len(result) == 1
        assert result[0]["name"] == "repo2"

    def test_filter_repositories_with_missing_owner(self):
        """Test that search handles missing owner field."""
        repos = [
            {"name": "repo1", "description": "Test"},
            {"name": "repo2", "owner": {"login": "testuser"}},
            {"name": "repo3", "owner": {}}
        ]

        result = filter_repositories(repos, "testuser")
        assert len(result) == 1
        assert result[0]["name"] == "repo2"

    def test_filter_repositories_special_characters(self):
        """Test that search handles special characters in query."""
        repos = [
            {"name": "repo-with-dashes", "description": "Test", "language": "Python"},
            {"name": "repo_with_underscores", "description": "Test", "language": "Python"},
            {"name": "repo.with.dots", "description": "Test", "language": "Python"}
        ]

        result_dashes = filter_repositories(repos, "with-dashes")
        assert len(result_dashes) == 1

        result_underscores = filter_repositories(repos, "with_underscores")
        assert len(result_underscores) == 1

        result_dots = filter_repositories(repos, "with.dots")
        assert len(result_dots) == 1

    def test_filter_repositories_long_query(self):
        """Test that search handles very long queries."""
        repos = [
            {"name": "repo", "description": "A very long description that contains many words and should be searchable", "language": "Python"}
        ]

        long_query = "very long description that contains many words"
        result = filter_repositories(repos, long_query)

        assert len(result) == 1

    def test_filter_repositories_empty_list(self):
        """Test that search handles empty repository list."""
        result = filter_repositories([], "python")

        assert len(result) == 0
        assert result == []

    def test_filter_repositories_numeric_characters(self):
        """Test that search handles numeric characters."""
        repos = [
            {"name": "repo-v2", "description": "Version 2 repository", "language": "Python"},
            {"name": "normal-repo", "description": "Normal description", "language": "Python"}
        ]

        result = filter_repositories(repos, "v2")
        assert len(result) == 1
        assert result[0]["name"] == "repo-v2"


# =============================================================================
# Get User Repositories Endpoint Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.activity
class TestGetUserRepositoriesEndpoint:
    """Test the GET /api/v1/activity/repositories endpoint."""

    @pytest.mark.asyncio
    async def test_get_repositories_success_no_query(
        self,
        client,
        sample_user_in_db,
        sample_github_repos
    ):
        """Test successful retrieval of all repositories without search query."""
        from app.routes.dependencies import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: sample_user_in_db

        try:
            with patch("app.routes.activity.GitHubService") as mock_service_class:
                mock_service = Mock()
                mock_service.get_user_repos = AsyncMock(return_value=sample_github_repos)
                mock_service_class.return_value = mock_service

                response = client.get("/api/v1/activity/repositories")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "repositories" in data
                assert len(data["repositories"]) == len(sample_github_repos)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_repositories_with_search_query(
        self,
        client,
        sample_user_in_db
    ):
        """Test retrieval of repositories with search query parameter."""
        from app.routes.dependencies import get_current_user
        from app.main import app

        repos = [
            {"name": "fastapi-app", "description": "API", "language": "Python"},
            {"name": "django-app", "description": "Web", "language": "Python"},
            {"name": "react-app", "description": "Frontend", "language": "JavaScript"}
        ]

        app.dependency_overrides[get_current_user] = lambda: sample_user_in_db

        try:
            with patch("app.routes.activity.GitHubService") as mock_service_class:
                mock_service = Mock()
                mock_service.get_user_repos = AsyncMock(return_value=repos)
                mock_service_class.return_value = mock_service

                response = client.get("/api/v1/activity/repositories?q=fastapi")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data["repositories"]) == 1
                assert data["repositories"][0]["name"] == "fastapi-app"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_repositories_search_no_results(
        self,
        client,
        sample_user_in_db,
        sample_github_repos
    ):
        """Test search query that returns no results."""
        from app.routes.dependencies import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: sample_user_in_db

        try:
            with patch("app.routes.activity.GitHubService") as mock_service_class:
                mock_service = Mock()
                mock_service.get_user_repos = AsyncMock(return_value=sample_github_repos)
                mock_service_class.return_value = mock_service

                response = client.get("/api/v1/activity/repositories?q=nonexistent")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data["repositories"]) == 0
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_repositories_missing_github_token(
        self,
        client,
        sample_user_in_db
    ):
        """Test that request fails when user has no GitHub access token."""
        from app.routes.dependencies import get_current_user
        from app.main import app

        user_no_token = sample_user_in_db.model_copy()
        user_no_token.github_access_token = None

        app.dependency_overrides[get_current_user] = lambda: user_no_token

        try:
            response = client.get("/api/v1/activity/repositories")

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "GitHub access token not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_repositories_github_api_error(
        self,
        client,
        sample_user_in_db
    ):
        """Test handling of GitHub API errors."""
        from app.routes.dependencies import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: sample_user_in_db

        try:
            with patch("app.routes.activity.GitHubService") as mock_service_class:
                mock_service = Mock()
                mock_service.get_user_repos = AsyncMock(
                    side_effect=Exception("401 Unauthorized")
                )
                mock_service_class.return_value = mock_service

                response = client.get("/api/v1/activity/repositories")

                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

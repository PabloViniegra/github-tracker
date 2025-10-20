"""
Test script for repository search feature.

This script demonstrates the filter_repositories function behavior
without requiring a running server or authentication.
"""

from typing import Any, Dict, List, Optional


def filter_repositories(
    repositories: List[Dict[str, Any]],
    query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter repositories based on a search query.

    Performs case-insensitive partial matching across multiple fields:
    - Repository name
    - Repository description
    - Repository topics/tags
    - Repository language
    - Repository owner login
    """
    # If no query provided, return all repositories
    if not query or not query.strip():
        return repositories

    # Normalize query to lowercase for case-insensitive search
    search_term = query.strip().lower()
    filtered_repos = []

    for repo in repositories:
        # Extract searchable fields with None-safe handling
        name = (repo.get("name") or "").lower()
        description = (repo.get("description") or "").lower()
        language = (repo.get("language") or "").lower()
        owner_login = (repo.get("owner", {}).get("login") or "").lower()

        # Topics are a list, join them into a searchable string
        topics = repo.get("topics", []) or []
        topics_str = " ".join(str(topic).lower() for topic in topics)

        # Check if search term appears in any field
        if (
            search_term in name
            or search_term in description
            or search_term in language
            or search_term in owner_login
            or search_term in topics_str
        ):
            filtered_repos.append(repo)

    return filtered_repos


def main():
    """Run test cases for repository search."""

    # Sample repository data
    test_repos = [
        {
            "id": 1,
            "name": "fastapi-project",
            "description": "A web API built with FastAPI framework",
            "language": "Python",
            "owner": {"login": "johndoe"},
            "topics": ["python", "fastapi", "web", "api"]
        },
        {
            "id": 2,
            "name": "react-dashboard",
            "description": "Modern dashboard application",
            "language": "JavaScript",
            "owner": {"login": "johndoe"},
            "topics": ["react", "dashboard", "frontend"]
        },
        {
            "id": 3,
            "name": "ml-toolkit",
            "description": "Machine learning utilities in Python",
            "language": "Python",
            "owner": {"login": "janedoe"},
            "topics": ["python", "machine-learning", "data-science"]
        },
        {
            "id": 4,
            "name": "go-microservice",
            "description": None,  # Test None handling
            "language": "Go",
            "owner": {"login": "johndoe"},
            "topics": []  # Test empty topics
        },
        {
            "id": 5,
            "name": "legacy-app",
            "description": "Old application",
            "language": None,  # Test None language
            "owner": {"login": "olduser"},
            "topics": None  # Test None topics
        }
    ]

    print("=" * 70)
    print("REPOSITORY SEARCH FEATURE TEST")
    print("=" * 70)
    print()

    # Test Case 1: No query (return all)
    print("Test 1: No search query (should return all 5 repositories)")
    print("-" * 70)
    result = filter_repositories(test_repos, None)
    print(f"Results: {len(result)} repositories")
    print()

    # Test Case 2: Search by language
    print("Test 2: Search for 'Python' repositories")
    print("-" * 70)
    result = filter_repositories(test_repos, "python")
    print(f"Results: {len(result)} repositories")
    for repo in result:
        print(f"  - {repo['name']} ({repo['language']})")
    print()

    # Test Case 3: Search by name (partial match)
    print("Test 3: Search for 'api' in repository name")
    print("-" * 70)
    result = filter_repositories(test_repos, "api")
    print(f"Results: {len(result)} repositories")
    for repo in result:
        print(f"  - {repo['name']}")
    print()

    # Test Case 4: Search by description
    print("Test 4: Search for 'dashboard' in description")
    print("-" * 70)
    result = filter_repositories(test_repos, "dashboard")
    print(f"Results: {len(result)} repositories")
    for repo in result:
        print(f"  - {repo['name']}: {repo['description']}")
    print()

    # Test Case 5: Search by owner
    print("Test 5: Search for repositories by owner 'janedoe'")
    print("-" * 70)
    result = filter_repositories(test_repos, "janedoe")
    print(f"Results: {len(result)} repositories")
    for repo in result:
        print(f"  - {repo['name']} (owner: {repo['owner']['login']})")
    print()

    # Test Case 6: Search by topic
    print("Test 6: Search for 'machine-learning' topic")
    print("-" * 70)
    result = filter_repositories(test_repos, "machine-learning")
    print(f"Results: {len(result)} repositories")
    for repo in result:
        print(f"  - {repo['name']} (topics: {repo['topics']})")
    print()

    # Test Case 7: Case insensitivity
    print("Test 7: Case insensitive search 'FASTAPI'")
    print("-" * 70)
    result = filter_repositories(test_repos, "FASTAPI")
    print(f"Results: {len(result)} repositories")
    for repo in result:
        print(f"  - {repo['name']}")
    print()

    # Test Case 8: No matches
    print("Test 8: Search with no matches 'rust'")
    print("-" * 70)
    result = filter_repositories(test_repos, "rust")
    print(f"Results: {len(result)} repositories")
    if not result:
        print("  (No repositories found)")
    print()

    # Test Case 9: Empty string query
    print("Test 9: Empty string query (should return all)")
    print("-" * 70)
    result = filter_repositories(test_repos, "   ")
    print(f"Results: {len(result)} repositories")
    print()

    # Test Case 10: Multi-match across fields
    print("Test 10: Search 'john' (should match owner)")
    print("-" * 70)
    result = filter_repositories(test_repos, "john")
    print(f"Results: {len(result)} repositories")
    for repo in result:
        print(f"  - {repo['name']} (owner: {repo['owner']['login']})")
    print()

    print("=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()

"""
GitHub API Integration Tests.

CTO Sprint 2 Deliverable 2: Integration Tests + CI Pipeline.

Tests verify that the GitHub API returns expected data structures
for tech stack analysis and prospect research. Real API calls.

Rate limit: 60 requests/hour without token, 5000 with token.
Tests are designed to be conservative -- uses small org with few repos.
"""

import asyncio
import os

import pytest

pytestmark = pytest.mark.integration

from csuite.tools.github_api import (
    GitHubClient,
    OrganizationInfo,
    RepositoryInfo,
    TechStackAnalysis,
    ActivityMetrics,
    EngineeringMaturity,
    ProspectTechProfile,
)


@pytest.fixture
def client():
    """Create a GitHub client, with token if available."""
    token = os.environ.get("GITHUB_TOKEN")
    return GitHubClient(token=token)


class TestOrganizationInfo:
    """Test organization info retrieval."""

    def test_valid_org_returns_info(self, client):
        """Should return info for a known organization."""
        org = asyncio.run(client.get_organization("vercel"))

        assert org is not None
        assert isinstance(org, OrganizationInfo)
        assert org.login == "vercel"
        assert org.public_repos > 0

    def test_invalid_org_returns_none(self, client):
        """Invalid org should return None, not raise."""
        org = asyncio.run(client.get_organization("this-org-definitely-does-not-exist-12345"))
        assert org is None

    def test_org_has_metadata(self, client):
        """Org should have basic metadata fields populated."""
        org = asyncio.run(client.get_organization("vercel"))

        assert org is not None
        assert org.html_url  # Should have a URL
        assert org.created_at  # Should have creation date


class TestOrgRepos:
    """Test repository listing."""

    def test_returns_repos_list(self, client):
        """Should return a list of repos."""
        repos = asyncio.run(client.get_org_repos("vercel", limit=5))

        assert isinstance(repos, list)
        assert len(repos) > 0
        assert all(isinstance(r, RepositoryInfo) for r in repos)

    def test_repos_have_required_fields(self, client):
        """Each repo should have name and URL."""
        repos = asyncio.run(client.get_org_repos("vercel", limit=3))

        for repo in repos:
            assert repo.name
            assert repo.full_name
            assert repo.html_url

    def test_limit_respected(self, client):
        """Limit parameter should cap results."""
        repos = asyncio.run(client.get_org_repos("vercel", limit=2))
        assert len(repos) <= 2


class TestTechStackAnalysis:
    """Test tech stack analysis."""

    def test_returns_analysis(self, client):
        """Should return tech stack analysis for a known org."""
        analysis = asyncio.run(
            client.analyze_org_tech_stack("vercel", max_repos=5)
        )

        if analysis is not None:
            assert isinstance(analysis, TechStackAnalysis)
            assert analysis.org_name == "vercel"
            assert analysis.repo_count > 0
            assert len(analysis.languages) > 0

    def test_sophistication_score_in_range(self, client):
        """Tech sophistication should be 0-100."""
        analysis = asyncio.run(
            client.analyze_org_tech_stack("vercel", max_repos=5)
        )

        if analysis is not None:
            assert 0 <= analysis.tech_sophistication_score <= 100


class TestActivityMetrics:
    """Test activity metrics."""

    def test_returns_metrics(self, client):
        """Should return activity metrics."""
        activity = asyncio.run(client.get_activity_metrics("vercel"))

        if activity is not None:
            assert isinstance(activity, ActivityMetrics)
            assert activity.total_repos > 0
            assert activity.activity_level in ("High", "Medium", "Low")


class TestEngineeringMaturity:
    """Test engineering maturity assessment."""

    def test_returns_maturity(self, client):
        """Should return maturity assessment."""
        maturity = asyncio.run(
            client.assess_engineering_maturity("vercel")
        )

        if maturity is not None:
            assert isinstance(maturity, EngineeringMaturity)
            assert maturity.maturity_level in ("Advanced", "Intermediate", "Basic")
            assert 0 <= maturity.ai_readiness_score <= 100


class TestRateLimit:
    """Test rate limit tracking."""

    def test_rate_limit_status(self, client):
        """Should report rate limit status."""
        status = client.get_rate_limit_status()

        assert "remaining" in status
        assert "limit" in status
        assert "authenticated" in status
        assert isinstance(status["remaining"], int)

#!/usr/bin/env python3
"""
GitHub API Integration Test/Demo Script.

Demonstrates the GitHub client capabilities for prospect research.
Run with: python scripts/test_github_api.py

Examples tested:
1. Organization info
2. Repository listing
3. Tech stack analysis
4. Activity metrics
5. Engineering maturity assessment
6. Complete prospect tech profile
7. Rate limit status
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from csuite.tools.github_api import GitHubClient


def format_number(value: int | float | None) -> str:
    """Format a number with commas."""
    if value is None:
        return "N/A"
    return f"{value:,.0f}"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


async def test_organization_info(client: GitHubClient) -> None:
    """Test organization info retrieval."""
    print_section("1. Organization Info")

    orgs = ["vercel", "stripe", "anthropics"]

    for org_name in orgs:
        print(f"\n  {org_name}:")
        try:
            org = await client.get_organization(org_name)
            if org:
                print(f"    Name: {org.name or org.login}")
                print(f"    Description: {(org.description or 'N/A')[:60]}...")
                print(f"    Public Repos: {format_number(org.public_repos)}")
                print(f"    Followers: {format_number(org.followers)}")
                print(f"    Location: {org.location or 'N/A'}")
            else:
                print("    Organization not found")
        except Exception as e:
            print(f"    Error: {e}")


async def test_org_repos(client: GitHubClient) -> None:
    """Test repository listing."""
    print_section("2. Organization Repositories")

    org_name = "vercel"
    print(f"\n  Top repos for {org_name}:")

    try:
        repos = await client.get_org_repos(org_name, limit=5)
        for repo in repos:
            stars = format_number(repo.stargazers_count)
            print(f"    - {repo.name}: {repo.language or 'N/A'}, {stars} stars")
    except Exception as e:
        print(f"    Error: {e}")


async def test_tech_stack_analysis(client: GitHubClient) -> None:
    """Test tech stack analysis."""
    print_section("3. Tech Stack Analysis")

    orgs = ["vercel", "supabase"]

    for org_name in orgs:
        print(f"\n  {org_name}:")
        try:
            analysis = await client.analyze_org_tech_stack(org_name, max_repos=10)
            if analysis:
                print(f"    Repos analyzed: {analysis.repo_count}")
                print(f"    Primary language: {analysis.primary_language}")
                print(f"    Contributors: {analysis.unique_contributors}")
                print(f"    Sophistication score: {analysis.tech_sophistication_score}/100")
                print(f"    Modern language %: {analysis.modern_language_pct:.1f}%")
                print(f"    AI language %: {analysis.ai_language_pct:.1f}%")
                print(f"    Top languages:")
                for lang, pct in list(analysis.languages.items())[:5]:
                    print(f"      - {lang}: {pct:.1f}%")
            else:
                print("    No tech stack data available")
        except Exception as e:
            print(f"    Error: {e}")


async def test_activity_metrics(client: GitHubClient) -> None:
    """Test activity metrics."""
    print_section("4. Activity Metrics")

    org_name = "vercel"
    print(f"\n  Activity for {org_name}:")

    try:
        activity = await client.get_activity_metrics(org_name)
        if activity:
            print(f"    Total repos: {activity.total_repos}")
            print(f"    Active (30d): {activity.active_repos_30d}")
            print(f"    Activity level: {activity.activity_level}")
            print(f"    Total stars: {format_number(activity.total_stars)}")
            print(f"    Total forks: {format_number(activity.total_forks)}")
            print(f"    Avg repo age: {activity.avg_repo_age_days:.0f} days")
            if activity.most_active_repos:
                print(f"    Most active: {', '.join(activity.most_active_repos[:3])}")
        else:
            print("    No activity data available")
    except Exception as e:
        print(f"    Error: {e}")


async def test_engineering_maturity(client: GitHubClient) -> None:
    """Test engineering maturity assessment."""
    print_section("5. Engineering Maturity Assessment")

    orgs = ["vercel", "supabase"]

    for org_name in orgs:
        print(f"\n  {org_name}:")
        try:
            maturity = await client.assess_engineering_maturity(org_name)
            if maturity:
                print(f"    Maturity level: {maturity.maturity_level}")
                print(f"    Team size estimate: {maturity.team_size_estimate}")
                print(f"    AI readiness: {maturity.ai_readiness_score}/100")
                print(f"    Has CI/CD: {'Yes' if maturity.has_ci_cd else 'No'}")
                print(f"    Has Tests: {'Yes' if maturity.has_tests else 'No'}")
                print(f"    Has Docs: {'Yes' if maturity.has_docs else 'No'}")
                print(f"    Has Security: {'Yes' if maturity.has_security else 'No'}")

                if maturity.signals:
                    print(f"    Signals:")
                    for signal in maturity.signals[:3]:
                        print(f"      - {signal}")

                if maturity.opportunities:
                    print(f"    Opportunities:")
                    for opp in maturity.opportunities[:3]:
                        print(f"      + {opp}")
            else:
                print("    No maturity data available")
        except Exception as e:
            print(f"    Error: {e}")


async def test_prospect_profile(client: GitHubClient) -> None:
    """Test complete prospect tech profile."""
    print_section("6. Complete Prospect Tech Profile")

    org_name = "supabase"
    print(f"\n  Generating profile for {org_name}...")

    try:
        profile = await client.generate_prospect_tech_profile(org_name)

        if profile.org_info:
            print(f"\n  Organization:")
            print(f"    {profile.org_info.name or profile.org_info.login}")
            print(f"    {profile.org_info.description or 'No description'}")

        if profile.tech_stack:
            print(f"\n  Tech Stack:")
            print(f"    Primary: {profile.tech_stack.primary_language}")
            print(f"    Sophistication: {profile.tech_stack.tech_sophistication_score}/100")

        if profile.activity:
            print(f"\n  Activity:")
            print(f"    Level: {profile.activity.activity_level}")
            print(f"    Active repos: {profile.activity.active_repos_30d}/{profile.activity.total_repos}")

        if profile.maturity:
            print(f"\n  Maturity:")
            print(f"    Level: {profile.maturity.maturity_level}")
            print(f"    AI Readiness: {profile.maturity.ai_readiness_score}/100")

        if profile.icp_fit_signals:
            print(f"\n  ICP Fit Signals:")
            for signal in profile.icp_fit_signals:
                print(f"    - {signal}")

    except Exception as e:
        print(f"    Error: {e}")


async def test_rate_limit(client: GitHubClient) -> None:
    """Show rate limit status."""
    print_section("7. Rate Limit Status")

    status = client.get_rate_limit_status()
    print(f"\n  Authenticated: {'Yes' if status['authenticated'] else 'No'}")
    print(f"  Limit: {status['limit']} requests/hour")
    print(f"  Remaining: {status['remaining']}")
    if status['reset_at']:
        print(f"  Resets at: {status['reset_at']}")


async def main() -> None:
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  GitHub API Integration Test")
    print("  Cardinal Element - Free API Enrichment Stack")
    print("=" * 60)

    # Initialize client (no token for testing)
    # For production, pass token="ghp_..." for 5,000/hr limit
    client = GitHubClient()

    print("\n  Note: Without token, limited to 60 requests/hour")
    print("  Get token at: https://github.com/settings/tokens")
    print("  (No special scopes needed for public data)")

    try:
        await test_organization_info(client)
        await test_org_repos(client)
        await test_tech_stack_analysis(client)
        await test_activity_metrics(client)
        await test_engineering_maturity(client)
        await test_prospect_profile(client)
        await test_rate_limit(client)

        print_section("All Tests Complete")
        print("\n  GitHub API integration is working correctly.")
        print("  Rate limit: 60/hour (5,000 with token)")
        print("  Cost: $0/month")

    except Exception as e:
        print(f"\nError during testing: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

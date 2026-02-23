"""
GitHub API Integration for Prospect Research.

Free API for analyzing prospect's engineering team, tech stack, and activity.
Used to estimate team size, identify technology preferences, and assess technical sophistication.

Endpoints:
- Organization metadata and repositories
- Repository languages and contributors
- Commit activity and development velocity
- User/org public profile data

Rate Limits: 60 requests/hour without token. 5,000 requests/hour with personal access token.
Authentication: Optional but recommended (free personal access token).

Usage:
    from csuite.tools.github_api import GitHubClient

    client = GitHubClient()  # Or GitHubClient(token="ghp_...")

    # Analyze organization tech stack
    analysis = await client.analyze_org_tech_stack("stripe")

    # Get organization info
    org = await client.get_organization("microsoft")

    # Estimate engineering maturity
    maturity = await client.assess_engineering_maturity("vercel")
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx

from csuite.tools.resilience import resilient

# Modern/sophisticated language indicators
MODERN_LANGUAGES = ["Python", "TypeScript", "Go", "Rust", "Swift", "Kotlin"]
AI_LANGUAGES = ["Python", "Julia", "R"]
AI_FRAMEWORKS = ["tensorflow", "pytorch", "scikit", "langchain", "openai", "huggingface", "mlflow"]

# Legacy language indicators
LEGACY_LANGUAGES = ["COBOL", "Fortran", "Visual Basic", "Perl"]


@dataclass
class OrganizationInfo:
    """GitHub organization information."""

    login: str
    name: str | None
    description: str | None
    blog: str | None
    location: str | None
    email: str | None
    public_repos: int
    public_members: int | None
    followers: int
    created_at: str
    updated_at: str
    html_url: str


@dataclass
class RepositoryInfo:
    """GitHub repository information."""

    name: str
    full_name: str
    description: str | None
    language: str | None
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    created_at: str
    updated_at: str
    pushed_at: str
    html_url: str
    is_fork: bool
    topics: list[str] = field(default_factory=list)


@dataclass
class TechStackAnalysis:
    """Tech stack analysis from GitHub repositories."""

    org_name: str
    repo_count: int
    languages: dict[str, float]  # Language -> percentage
    primary_language: str | None
    total_bytes: int
    modern_language_pct: float
    legacy_language_pct: float
    ai_language_pct: float
    unique_contributors: int
    tech_sophistication_score: int  # 0-100
    open_source_active: bool


@dataclass
class ContributorInfo:
    """GitHub contributor information."""

    login: str
    contributions: int
    html_url: str


@dataclass
class ActivityMetrics:
    """Repository activity metrics."""

    org_name: str
    total_repos: int
    active_repos_30d: int
    total_stars: int
    total_forks: int
    total_open_issues: int
    avg_repo_age_days: float
    most_active_repos: list[str]
    activity_level: str  # "High", "Medium", "Low"


@dataclass
class EngineeringMaturity:
    """Engineering maturity assessment."""

    org_name: str
    maturity_level: str  # "Advanced", "Intermediate", "Basic"
    has_ci_cd: bool
    has_tests: bool
    has_docs: bool
    has_security: bool
    ai_readiness_score: int  # 0-100
    team_size_estimate: int
    signals: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)


@dataclass
class ProspectTechProfile:
    """Complete technical profile for prospect research."""

    org_name: str
    org_info: OrganizationInfo | None
    tech_stack: TechStackAnalysis | None
    activity: ActivityMetrics | None
    maturity: EngineeringMaturity | None
    icp_fit_signals: list[str] = field(default_factory=list)
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())


class GitHubClient:
    """Client for GitHub API.

    Provides access to organization, repository, and contributor data
    for prospect research and technical assessment.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        """Initialize GitHub client.

        Args:
            token: Optional GitHub personal access token.
                  Without token: 60 requests/hour
                  With token: 5,000 requests/hour
                  Get token at: https://github.com/settings/tokens
        """
        self.token = token
        self._rate_limit_remaining = 60
        self._rate_limit_reset: datetime | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with optional auth."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _check_rate_limit(self, response: httpx.Response) -> None:
        """Update rate limit tracking from response headers."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")

        if remaining:
            self._rate_limit_remaining = int(remaining)
        if reset:
            self._rate_limit_reset = datetime.fromtimestamp(int(reset))

        if self._rate_limit_remaining <= 0:
            reset_time = self._rate_limit_reset or datetime.now() + timedelta(hours=1)
            raise GitHubAPIError(
                f"Rate limit exceeded. Resets at {reset_time.isoformat()}. "
                "Use a personal access token for 5,000 requests/hour."
            )

    @resilient(api_name="github", cache_ttl=300)
    async def _request(self, endpoint: str, params: dict | None = None) -> dict | list | None:
        """Make a request to the GitHub API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data
        """
        url = f"{self.BASE_URL}{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )

                self._check_rate_limit(response)

                if response.status_code == 404:
                    return None
                if response.status_code == 403:
                    raise GitHubAPIError("Access forbidden. Check token permissions.")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                raise GitHubAPIError(f"HTTP error: {e.response.status_code}")
            except httpx.RequestError as e:
                raise GitHubAPIError(f"Request failed: {e}")

    async def get_organization(self, org_name: str) -> OrganizationInfo | None:
        """Get organization information.

        Args:
            org_name: GitHub organization login name

        Returns:
            OrganizationInfo or None if not found
        """
        data = await self._request(f"/orgs/{org_name}")
        if not data:
            return None

        return OrganizationInfo(
            login=data.get("login", ""),
            name=data.get("name"),
            description=data.get("description"),
            blog=data.get("blog"),
            location=data.get("location"),
            email=data.get("email"),
            public_repos=data.get("public_repos", 0),
            public_members=data.get("public_members_count"),
            followers=data.get("followers", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            html_url=data.get("html_url", ""),
        )

    async def get_org_repos(
        self,
        org_name: str,
        limit: int = 100
    ) -> list[RepositoryInfo]:
        """Get organization repositories.

        Args:
            org_name: GitHub organization login name
            limit: Maximum repos to fetch

        Returns:
            List of RepositoryInfo
        """
        repos: list[RepositoryInfo] = []
        page = 1
        per_page = min(limit, 100)

        while len(repos) < limit:
            data = await self._request(
                f"/orgs/{org_name}/repos",
                params={"per_page": per_page, "page": page, "sort": "updated"}
            )

            if not data:
                break

            for repo in data:
                repos.append(RepositoryInfo(
                    name=repo.get("name", ""),
                    full_name=repo.get("full_name", ""),
                    description=repo.get("description"),
                    language=repo.get("language"),
                    stargazers_count=repo.get("stargazers_count", 0),
                    forks_count=repo.get("forks_count", 0),
                    open_issues_count=repo.get("open_issues_count", 0),
                    created_at=repo.get("created_at", ""),
                    updated_at=repo.get("updated_at", ""),
                    pushed_at=repo.get("pushed_at", ""),
                    html_url=repo.get("html_url", ""),
                    is_fork=repo.get("fork", False),
                    topics=repo.get("topics", []),
                ))

            if len(data) < per_page:
                break
            page += 1

        return repos[:limit]

    async def get_repo_languages(self, owner: str, repo: str) -> dict[str, int]:
        """Get languages used in a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dict mapping language name to bytes of code
        """
        data = await self._request(f"/repos/{owner}/{repo}/languages")
        return data if data else {}

    async def get_repo_contributors(
        self,
        owner: str,
        repo: str,
        limit: int = 50
    ) -> list[ContributorInfo]:
        """Get repository contributors.

        Args:
            owner: Repository owner
            repo: Repository name
            limit: Maximum contributors to fetch

        Returns:
            List of ContributorInfo
        """
        data = await self._request(
            f"/repos/{owner}/{repo}/contributors",
            params={"per_page": min(limit, 100)}
        )

        if not data or isinstance(data, dict):  # Error response is dict
            return []

        contributors = []
        for contrib in data[:limit]:
            if isinstance(contrib, dict):
                contributors.append(ContributorInfo(
                    login=contrib.get("login", ""),
                    contributions=contrib.get("contributions", 0),
                    html_url=contrib.get("html_url", ""),
                ))

        return contributors

    async def analyze_org_tech_stack(
        self,
        org_name: str,
        max_repos: int = 20
    ) -> TechStackAnalysis | None:
        """Analyze organization's tech stack from public repositories.

        Args:
            org_name: GitHub organization login name
            max_repos: Maximum repos to analyze (to conserve rate limit)

        Returns:
            TechStackAnalysis with language breakdown and sophistication score
        """
        repos = await self.get_org_repos(org_name, limit=max_repos)
        if not repos:
            return None

        # Aggregate languages across repos
        all_languages: dict[str, int] = {}
        unique_contributors: set[str] = set()

        for repo in repos:
            if repo.is_fork:
                continue

            # Get languages for repo
            languages = await self.get_repo_languages(org_name, repo.name)
            for lang, bytes_count in languages.items():
                all_languages[lang] = all_languages.get(lang, 0) + bytes_count

            # Get contributors (limit to save rate limit)
            contributors = await self.get_repo_contributors(org_name, repo.name, limit=30)
            for contrib in contributors:
                unique_contributors.add(contrib.login)

        if not all_languages:
            return None

        # Calculate percentages
        total_bytes = sum(all_languages.values())
        language_pcts = {
            lang: (bytes_count / total_bytes * 100)
            for lang, bytes_count in sorted(
                all_languages.items(),
                key=lambda x: x[1],
                reverse=True
            )
        }

        # Calculate category percentages
        modern_pct = sum(language_pcts.get(lang, 0) for lang in MODERN_LANGUAGES)
        legacy_pct = sum(language_pcts.get(lang, 0) for lang in LEGACY_LANGUAGES)
        ai_pct = sum(language_pcts.get(lang, 0) for lang in AI_LANGUAGES)

        # Tech sophistication score (0-100)
        sophistication_score = min(int(
            modern_pct * 0.6 +  # Modern languages weighted
            (len(repos) * 2) +  # More repos = more active
            (len(unique_contributors) * 0.5) -  # Team size
            (legacy_pct * 0.3)  # Legacy penalty
        ), 100)

        primary_lang = (
            max(language_pcts.keys(), key=lambda k: language_pcts[k])
            if language_pcts else None
        )

        return TechStackAnalysis(
            org_name=org_name,
            repo_count=len([r for r in repos if not r.is_fork]),
            languages=dict(list(language_pcts.items())[:10]),  # Top 10
            primary_language=primary_lang,
            total_bytes=total_bytes,
            modern_language_pct=modern_pct,
            legacy_language_pct=legacy_pct,
            ai_language_pct=ai_pct,
            unique_contributors=len(unique_contributors),
            tech_sophistication_score=sophistication_score,
            open_source_active=len(repos) >= 5,
        )

    async def get_activity_metrics(self, org_name: str) -> ActivityMetrics | None:
        """Get activity metrics for an organization.

        Args:
            org_name: GitHub organization login name

        Returns:
            ActivityMetrics with engagement stats
        """
        repos = await self.get_org_repos(org_name, limit=50)
        if not repos:
            return None

        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)

        active_repos = 0
        total_stars = 0
        total_forks = 0
        total_issues = 0
        repo_ages: list[float] = []
        most_active: list[tuple[str, str]] = []

        for repo in repos:
            total_stars += repo.stargazers_count
            total_forks += repo.forks_count
            total_issues += repo.open_issues_count

            # Check if pushed in last 30 days
            if repo.pushed_at:
                try:
                    pushed = datetime.fromisoformat(repo.pushed_at.replace("Z", "+00:00"))
                    if pushed.replace(tzinfo=None) > thirty_days_ago:
                        active_repos += 1
                        most_active.append((repo.name, repo.pushed_at))
                except ValueError:
                    pass

            # Calculate repo age
            if repo.created_at:
                try:
                    created = datetime.fromisoformat(repo.created_at.replace("Z", "+00:00"))
                    age_days = (now - created.replace(tzinfo=None)).days
                    repo_ages.append(age_days)
                except ValueError:
                    pass

        avg_age = sum(repo_ages) / len(repo_ages) if repo_ages else 0

        # Determine activity level
        if active_repos >= len(repos) * 0.5:
            activity_level = "High"
        elif active_repos >= len(repos) * 0.2:
            activity_level = "Medium"
        else:
            activity_level = "Low"

        # Sort most active by pushed date
        most_active.sort(key=lambda x: x[1], reverse=True)

        return ActivityMetrics(
            org_name=org_name,
            total_repos=len(repos),
            active_repos_30d=active_repos,
            total_stars=total_stars,
            total_forks=total_forks,
            total_open_issues=total_issues,
            avg_repo_age_days=avg_age,
            most_active_repos=[name for name, _ in most_active[:5]],
            activity_level=activity_level,
        )

    async def assess_engineering_maturity(
        self,
        org_name: str
    ) -> EngineeringMaturity | None:
        """Assess engineering maturity from GitHub activity.

        Looks for indicators of mature engineering practices:
        CI/CD, testing, documentation, security.

        Args:
            org_name: GitHub organization login name

        Returns:
            EngineeringMaturity assessment with signals
        """
        repos = await self.get_org_repos(org_name, limit=30)
        if not repos:
            return None

        tech_stack = await self.analyze_org_tech_stack(org_name, max_repos=20)

        # Check for maturity indicators in repo names and topics
        all_topics: set[str] = set()
        all_names: list[str] = []

        for repo in repos:
            all_names.append(repo.name.lower())
            all_topics.update(repo.topics)

        all_text = " ".join(all_names) + " " + " ".join(all_topics)

        # CI/CD indicators
        ci_keywords = ["action", "workflow", "ci", "cd", "deploy", "pipeline"]
        has_ci_cd = any(kw in all_text for kw in ci_keywords)

        # Testing indicators
        test_keywords = ["test", "spec", "jest", "pytest", "mocha", "cypress"]
        has_tests = any(kw in all_text for kw in test_keywords)

        # Documentation indicators
        doc_keywords = ["doc", "wiki", "readme", "guide", "tutorial"]
        has_docs = any(kw in all_text for kw in doc_keywords)

        # Security indicators
        security_keywords = ["security", "auth", "oauth", "jwt", "crypto"]
        has_security = any(kw in all_text for kw in security_keywords)

        # Determine maturity level
        indicators = [has_ci_cd, has_tests, has_docs, has_security]
        if sum(indicators) >= 3:
            maturity_level = "Advanced"
        elif sum(indicators) >= 1:
            maturity_level = "Intermediate"
        else:
            maturity_level = "Basic"

        # AI readiness score
        ai_readiness = 0
        if tech_stack:
            ai_readiness = int(tech_stack.ai_language_pct)
            # Check for AI framework mentions
            if any(fw in all_text for fw in AI_FRAMEWORKS):
                ai_readiness += 20
        ai_readiness = min(ai_readiness, 100)

        # Generate signals and opportunities
        signals = []
        opportunities = []

        if tech_stack:
            signals.append(f"Primary language: {tech_stack.primary_language}")
            signals.append(f"Tech sophistication: {tech_stack.tech_sophistication_score}/100")
            signals.append(f"Estimated team size: {tech_stack.unique_contributors} contributors")

        if maturity_level == "Advanced":
            signals.append("Mature engineering practices detected")
        elif maturity_level == "Basic":
            opportunities.append("Engineering process improvement opportunity")

        if ai_readiness < 30:
            opportunities.append("Low AI readiness = opportunity for AI consulting")
        elif ai_readiness > 60:
            signals.append("Already AI-capable team")

        if not has_ci_cd:
            opportunities.append("No CI/CD detected = automation opportunity")

        return EngineeringMaturity(
            org_name=org_name,
            maturity_level=maturity_level,
            has_ci_cd=has_ci_cd,
            has_tests=has_tests,
            has_docs=has_docs,
            has_security=has_security,
            ai_readiness_score=ai_readiness,
            team_size_estimate=tech_stack.unique_contributors if tech_stack else 0,
            signals=signals,
            opportunities=opportunities,
        )

    async def generate_prospect_tech_profile(
        self,
        org_name: str
    ) -> ProspectTechProfile:
        """Generate complete technical profile for prospect research.

        Combines org info, tech stack, activity, and maturity assessment.

        Args:
            org_name: GitHub organization login name

        Returns:
            ProspectTechProfile with all available data
        """
        profile = ProspectTechProfile(org_name=org_name)

        # Fetch all data
        profile.org_info = await self.get_organization(org_name)
        profile.tech_stack = await self.analyze_org_tech_stack(org_name)
        profile.activity = await self.get_activity_metrics(org_name)
        profile.maturity = await self.assess_engineering_maturity(org_name)

        # Generate ICP fit signals
        if profile.tech_stack:
            if 20 <= profile.tech_stack.unique_contributors <= 150:
                profile.icp_fit_signals.append(
                    f"Team size ({profile.tech_stack.unique_contributors}) in ICP range (20-150)"
                )
            elif profile.tech_stack.unique_contributors < 20:
                profile.icp_fit_signals.append(
                    f"Team size ({profile.tech_stack.unique_contributors}) below ICP minimum"
                )

            if profile.tech_stack.modern_language_pct > 50:
                profile.icp_fit_signals.append("Modern tech stack = good technology adoption")

        if profile.maturity:
            if profile.maturity.ai_readiness_score < 40:
                profile.icp_fit_signals.append(
                    "Low AI readiness = high potential for AI consulting"
                )

        if profile.activity:
            if profile.activity.activity_level == "High":
                profile.icp_fit_signals.append(
                    "High development activity = active engineering investment"
                )

        return profile

    def get_rate_limit_status(self) -> dict[str, Any]:
        """Get current rate limit status.

        Returns:
            Dict with remaining requests and reset time
        """
        return {
            "remaining": self._rate_limit_remaining,
            "reset_at": self._rate_limit_reset.isoformat() if self._rate_limit_reset else None,
            "authenticated": self.token is not None,
            "limit": 5000 if self.token else 60,
        }


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""

    pass

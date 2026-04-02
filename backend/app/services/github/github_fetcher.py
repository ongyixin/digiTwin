"""GitHub content fetcher.

Fetches repository trees and file contents using the GitHub REST API.
For small/medium repos, uses the GitHub API directly (no cloning needed).
"""

import base64
from typing import Optional

import httpx

from app.services.github.github_app import GitHubAuth

# File extensions considered code/docs (skip binary assets, generated files)
_RELEVANT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".swift",
    ".md", ".rst", ".txt", ".yaml", ".yml", ".toml", ".json",
    ".sh", ".bash", ".dockerfile", ".tf",
}

_SKIP_DIRECTORIES = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", ".tox", "coverage", ".nyc_output",
}

# Max file size to fetch (50 KB)
_MAX_FILE_BYTES = 50_000


class GitHubFetcher:
    """Fetches repository structure and file contents from the GitHub API."""

    def __init__(self, installation_id: Optional[str] = None) -> None:
        self._auth = GitHubAuth(installation_id=installation_id)
        self._token: Optional[str] = None

    async def authenticate(self) -> None:
        self._token = await self._auth.get_token()

    def _headers(self) -> dict:
        return {
            "Authorization": f"token {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def enumerate_files(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
    ) -> list[str]:
        """Return a list of all relevant file paths in the repository tree."""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 404:
                # Try 'master' if 'main' not found
                url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
                resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            tree = resp.json().get("tree", [])

        relevant = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            path: str = item.get("path", "")
            # Skip irrelevant directories
            parts = path.split("/")
            if any(p in _SKIP_DIRECTORIES for p in parts):
                continue
            # Check extension
            ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
            if ext in _RELEVANT_EXTENSIONS:
                relevant.append(path)

        return relevant

    async def fetch_files(
        self,
        owner: str,
        repo: str,
        file_paths: list[str],
        max_files: int = 200,
        branch: str = "main",
    ) -> dict[str, str]:
        """Fetch content of up to max_files files. Returns {path: content}."""
        results: dict[str, str] = {}
        # Prioritize: README, docs, then source files
        prioritized = sorted(
            file_paths[:max_files],
            key=lambda p: (
                0 if p.lower() in ("readme.md", "readme.rst", "readme.txt") else
                1 if p.lower().startswith("docs/") else
                2 if p.endswith(".md") else
                3 if p.endswith((".yaml", ".yml", ".toml")) else
                4
            ),
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            for path in prioritized[:max_files]:
                try:
                    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
                    resp = await client.get(url, headers=self._headers())
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    if data.get("size", 0) > _MAX_FILE_BYTES:
                        continue
                    encoded = data.get("content", "")
                    if encoded:
                        content = base64.b64decode(encoded).decode("utf-8", errors="replace")
                        results[path] = content
                except Exception:
                    continue

        return results

    async def get_latest_sha(self, owner: str, repo: str, branch: str = "main") -> str:
        """Return the latest commit SHA for the branch."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("sha", "unknown")
        return "unknown"

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        limit: int = 50,
    ) -> list[dict]:
        """Fetch recent pull requests."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state={state}&per_page={limit}"
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
        return []

    async def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        limit: int = 50,
    ) -> list[dict]:
        """Fetch recent issues."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"https://api.github.com/repos/{owner}/{repo}/issues?state={state}&per_page={limit}&filter=all"
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
        return []

    async def fetch_commits(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        limit: int = 100,
    ) -> list[dict]:
        """Fetch commit history, returning sha, message, author, and date."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = (
                f"https://api.github.com/repos/{owner}/{repo}/commits"
                f"?sha={branch}&per_page={min(limit, 100)}"
            )
            resp = await client.get(url, headers=self._headers())
            if resp.status_code != 200:
                return []
            raw = resp.json()

        commits = []
        for c in raw:
            commit_data = c.get("commit", {})
            commits.append({
                "sha": c.get("sha", "")[:12],
                "message": commit_data.get("message", ""),
                "author": commit_data.get("author", {}).get("name", ""),
                "date": commit_data.get("author", {}).get("date", ""),
            })
        return commits

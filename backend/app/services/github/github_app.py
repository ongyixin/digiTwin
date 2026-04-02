"""GitHub App authentication.

Supports two modes:
1. GitHub App (recommended): JWT + installation tokens, fine-grained per-repo permissions
2. Personal Access Token (PAT): simpler, useful for development/demo

Set GITHUB_ACCESS_TOKEN for PAT mode.
Set GITHUB_APP_ID + GITHUB_APP_PRIVATE_KEY for GitHub App mode.
"""

import os
import time
from typing import Optional

import httpx


class GitHubAuth:
    """Handles GitHub authentication for API requests."""

    def __init__(self, installation_id: Optional[str] = None) -> None:
        self._pat = os.environ.get("GITHUB_ACCESS_TOKEN", "")
        self._app_id = os.environ.get("GITHUB_APP_ID", "")
        self._private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
        self._installation_id = installation_id or os.environ.get("GITHUB_INSTALLATION_ID", "")
        self._installation_token: Optional[str] = None
        self._token_expiry: float = 0.0

    async def get_token(self) -> str:
        """Return a valid access token for GitHub API calls."""
        if self._pat:
            return self._pat

        if self._app_id and self._private_key and self._installation_id:
            return await self._get_installation_token()

        raise ValueError(
            "No GitHub credentials configured. Set GITHUB_ACCESS_TOKEN "
            "or GITHUB_APP_ID + GITHUB_APP_PRIVATE_KEY + GITHUB_INSTALLATION_ID"
        )

    async def _get_installation_token(self) -> str:
        """Exchange a GitHub App JWT for an installation access token."""
        now = time.time()
        # Reuse cached token if still valid (tokens last 1 hour)
        if self._installation_token and now < self._token_expiry - 60:
            return self._installation_token

        jwt_token = self._create_jwt()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/app/installations/{self._installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._installation_token = data["token"]
            self._token_expiry = now + 3600
            return self._installation_token

    def _create_jwt(self) -> str:
        """Create a short-lived JWT for GitHub App authentication."""
        try:
            import jwt as pyjwt
        except ImportError:
            raise RuntimeError("PyJWT is required for GitHub App auth. Install: pip install PyJWT cryptography")

        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + 600,
            "iss": self._app_id,
        }
        return pyjwt.encode(payload, self._private_key, algorithm="RS256")

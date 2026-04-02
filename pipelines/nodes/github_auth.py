"""
RocketRide custom node: GitHub authentication and repository enumeration.

Actions:
  get_installation_token  — exchange App credentials for an installation token
                            (falls back to GITHUB_ACCESS_TOKEN when App creds absent)
  enumerate_repo          — fetch a filtered file listing from a GitHub repository
"""

import base64
import json
import os
import sys
import time
import urllib.request
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _http_get(url: str, headers: dict) -> Any:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _jwt_for_app(app_id: str, private_key_pem: str) -> str:
    """Minimal RS256 JWT using only stdlib — no PyJWT dependency."""
    import hashlib
    import hmac

    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        raise RuntimeError(
            "cryptography package is required for GitHub App JWT. "
            "Install it in the RocketRide engine environment."
        )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {"iat": now - 60, "exp": now + 540, "iss": app_id}

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None, backend=default_backend()
    )
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{h}.{p}.{_b64url(signature)}"


# ---------------------------------------------------------------------------
# Action: get_installation_token
# ---------------------------------------------------------------------------

def get_installation_token(payload: dict) -> dict:
    access_token = _env("GITHUB_ACCESS_TOKEN")
    app_id = _env("GITHUB_APP_ID")
    private_key = _env("GITHUB_APP_PRIVATE_KEY")
    installation_id = _env("GITHUB_INSTALLATION_ID")

    if app_id and private_key and installation_id:
        jwt = _jwt_for_app(app_id, private_key)
        data = _http_get(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        return {"token": data["token"], "source": "github_app"}

    if access_token:
        return {"token": access_token, "source": "personal_access_token"}

    raise RuntimeError("No GitHub credentials available (set GITHUB_ACCESS_TOKEN or GitHub App env vars)")


# ---------------------------------------------------------------------------
# Action: enumerate_repo
# ---------------------------------------------------------------------------

_DEFAULT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".go", ".java", ".rs",
    ".md", ".yaml", ".yml", ".toml", ".json",
}


def enumerate_repo(payload: dict) -> dict:
    token = payload.get("token", _env("GITHUB_ACCESS_TOKEN"))
    repo_url = payload.get("repo_url", payload.get("github_repo_url", ""))
    branch = payload.get("branch", "main")
    max_files: int = payload.get("max_files", 200)
    extensions = set(payload.get("relevant_extensions", list(_DEFAULT_EXTENSIONS)))

    # Extract owner/repo from URL
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse repo URL: {repo_url}")
    owner, repo = parts[-2], parts[-1].removesuffix(".git")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Get the git tree (recursive)
    tree_data = _http_get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
        headers,
    )

    files = []
    for item in tree_data.get("tree", []):
        if item["type"] != "blob":
            continue
        path: str = item["path"]
        ext = os.path.splitext(path)[1].lower()
        if ext not in extensions:
            continue
        files.append({"path": path, "sha": item["sha"], "size": item.get("size", 0)})
        if len(files) >= max_files:
            break

    return {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "files": files,
        "total_found": len(files),
        "truncated": tree_data.get("truncated", False),
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    payload = json.loads(sys.stdin.read())
    action = payload.get("action", "get_installation_token")

    if action == "get_installation_token":
        result = get_installation_token(payload)
    elif action == "enumerate_repo":
        result = enumerate_repo(payload)
    else:
        raise ValueError(f"Unknown action: {action}")

    print(json.dumps(result))


if __name__ == "__main__":
    main()

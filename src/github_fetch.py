"""Fetch public GitHub repository metadata to seed project config."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import requests

GITHUB_API = "https://api.github.com/repos/{owner}/{repo}"
README_API = "https://api.github.com/repos/{owner}/{repo}/readme"
TOPICS_API = "https://api.github.com/repos/{owner}/{repo}/topics"


def parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    parsed = urlparse(url)
    path = parsed.path.strip("/")
    match = re.match(r"^([^/]+)/([^/]+)$", path)
    if not match:
        raise ValueError(f"Not a valid GitHub repo URL: {url}")
    return match.group(1), match.group(2)


def fetch_repo(url: str, token: str | None = None) -> dict:
    owner, repo = parse_github_url(url)
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(GITHUB_API.format(owner=owner, repo=repo), headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    topics: list[str] = []
    topics_resp = requests.get(
        TOPICS_API.format(owner=owner, repo=repo),
        headers={**headers, "Accept": "application/vnd.github.mercy-preview+json"},
        timeout=30,
    )
    if topics_resp.ok:
        topics = topics_resp.json().get("names") or []

    readme_excerpt = ""
    readme_resp = requests.get(
        README_API.format(owner=owner, repo=repo),
        headers={**headers, "Accept": "application/vnd.github.raw"},
        timeout=30,
    )
    if readme_resp.ok:
        readme_excerpt = readme_resp.text[:2000]

    return {
        "owner": owner,
        "repo_name": repo,
        "repo_url": f"https://github.com/{owner}/{repo}",
        "description": data.get("description") or "",
        "topics": topics,
        "language": data.get("language") or "",
        "license": (data.get("license") or {}).get("spdx_id") or "MIT",
        "homepage": data.get("homepage") or "",
        "stars": data.get("stargazers_count", 0),
        "readme_excerpt": readme_excerpt,
    }


def repo_to_config_seed(repo: dict, niche: str = "") -> dict:
    """Build a minimal project config dict from fetched GitHub data."""
    repo_name = repo["repo_name"]
    description = repo["description"] or f"Open-source {repo_name} project"
    primary = description.split("—")[0].split("-")[0].strip() or repo_name.replace("-", " ")

    return {
        "project_name": repo_name,
        "niche": niche or "Open-source developer tools",
        "github": {
            "repo_url": repo["repo_url"],
            "repo_name": repo_name,
            "primary_keyword": primary,
            "short_description": description[:GITHUB_ABOUT_MAX] if description else primary,
            "topics": repo["topics"][:10] if repo["topics"] else [],
            "language": repo["language"],
            "license": repo["license"],
            "features": [],
            "tech_stack": [repo["language"]] if repo["language"] else [],
            "use_cases": [],
        },
        "youtube": {
            "channel_handle": "",
            "playlists": [],
            "videos": [],
        },
        "cross_links": {
            "website": repo.get("homepage") or "",
            "related_repos": [],
            "youtube_videos": [],
        },
        "social": {
            "enabled": True,
            "hashtags": [],
            "subreddits": [],
        },
    }


GITHUB_ABOUT_MAX = 350

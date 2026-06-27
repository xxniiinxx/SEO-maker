"""Detect whether a URL points to GitHub or YouTube."""

from __future__ import annotations

from urllib.parse import urlparse


def detect_url_type(url: str) -> str:
    """Return 'github', 'youtube_video', or 'youtube_channel'."""
    url = url.strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()

    if "github.com" in host or "github.io" in host:
        return "github"

    if host in {"youtu.be", "www.youtu.be"}:
        return "youtube_video"

    if "youtube.com" in host or "youtube-nocookie.com" in host:
        if path.startswith("/watch") or path.startswith("/shorts/") or path.startswith("/embed/"):
            return "youtube_video"
        if path.startswith("/@") or path.startswith("/channel/") or path.startswith("/c/") or path.startswith("/user/"):
            return "youtube_channel"

    raise ValueError(
        f"Unrecognized URL (expected GitHub repo or YouTube video/channel): {url}"
    )


def is_github_url(url: str) -> bool:
    return detect_url_type(url) == "github"


def is_youtube_url(url: str) -> bool:
    return detect_url_type(url) in {"youtube_video", "youtube_channel"}

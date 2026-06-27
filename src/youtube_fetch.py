"""Fetch public YouTube metadata to seed project config (no API key required)."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import requests

OEMBED_URL = "https://www.youtube.com/oembed"


def parse_video_id(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)

    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path.startswith("/shorts/"):
        video_id = parsed.path.split("/")[2]
    elif parsed.path.startswith("/embed/"):
        video_id = parsed.path.split("/")[2]
    else:
        query = parse_qs(parsed.query)
        video_id = query.get("v", [""])[0]

    if not re.match(r"^[\w-]{11}$", video_id):
        raise ValueError(f"Not a valid YouTube video URL: {url}")
    return video_id


def parse_channel_handle(url: str) -> str:
    url = url.strip().rstrip("/")
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if path.startswith("@"):
        return f"@{path.split('/')[0].lstrip('@')}"

    if path.startswith("channel/") or path.startswith("c/") or path.startswith("user/"):
        return path.split("/")[1]

    raise ValueError(f"Not a recognized YouTube channel URL: {url}")


def video_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def fetch_video(url: str) -> dict:
    video_id = parse_video_id(url)
    watch_url = video_watch_url(video_id)
    response = requests.get(
        OEMBED_URL,
        params={"url": watch_url, "format": "json"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    author_name = data.get("author_name") or ""
    author_url = data.get("author_url") or ""
    channel_handle = ""
    if "/@" in author_url:
        channel_handle = "@" + author_url.rstrip("/").split("/@")[-1].split("/")[0]
    elif author_name.startswith("@"):
        channel_handle = author_name.split()[0]

    title = data.get("title") or f"YouTube video {video_id}"
    return {
        "video_id": video_id,
        "url": watch_url,
        "title": title,
        "channel_handle": channel_handle,
        "author_name": author_name,
        "thumbnail_url": data.get("thumbnail_url") or "",
    }


def slugify_video_id(title: str, video_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)[:48].strip("-")
    return slug or video_id


def extract_video_keyword(title: str, repo_name: str = "") -> str:
    cleaned = re.sub(r"\s*[\|\-–—]\s*.*$", "", title)
    cleaned = re.sub(r"\s*\(\d{4}\)\s*", " ", cleaned)
    cleaned = re.sub(r"\s*\d{4}\s*", " ", cleaned)
    cleaned = cleaned.strip()
    if len(cleaned) >= 12:
        return cleaned
    human = repo_name.replace("-", " ").title()
    return f"{human} tutorial" if human else title[:60]


def extract_video_topic(title: str) -> str:
    return title.strip()


def extract_youtube_urls_from_text(text: str) -> list[str]:
    """Find YouTube watch URLs in README or other text."""
    if not text:
        return []
    patterns = [
        r"https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}[^\s\)]*",
        r"https?://(?:www\.)?youtu\.be/[\w-]{11}[^\s\)]*",
    ]
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            url = match.group(0).rstrip(").],>")
            if url not in found:
                found.append(url)
    return found


def setup_timestamps() -> list[str]:
    return [
        "0:00 Intro and disclaimer",
        "1:30 Prerequisites and environment",
        "4:00 Clone repo and install dependencies",
        "6:30 Configuration walkthrough",
        "9:00 Live demo",
        "11:00 GitHub link and next steps",
    ]


def overview_timestamps() -> list[str]:
    return [
        "0:00 Intro",
        "2:00 Architecture overview",
        "5:00 Live demo",
        "8:00 Key features recap",
        "10:00 Links and disclaimer",
    ]


def default_timestamps() -> list[str]:
    return [
        "0:00 Intro and disclaimer",
        "1:30 Overview",
        "4:00 Setup and walkthrough",
        "8:00 Demo",
        "10:00 Links and next steps",
    ]


def video_to_config_entry(
    video: dict,
    repo_name: str = "",
    topics: list[str] | None = None,
) -> tuple[dict, dict]:
    """Return (youtube.videos item, cross_links.youtube_videos item)."""
    topics = topics or []
    slug = slugify_video_id(video["title"], video["video_id"])
    year = str(datetime.now().year)
    keyword = extract_video_keyword(video["title"], repo_name)
    topic = extract_video_topic(video["title"])

    video_cfg = {
        "id": slug,
        "primary_keyword": keyword,
        "video_topic": topic,
        "year": year,
        "youtube_url": video["url"],
        "target_length_minutes": 10,
        "secondary_keywords": topics[:5],
        "timestamps": default_timestamps(),
    }
    cross_cfg = {
        "id": slug,
        "title": topic,
        "url": video["url"],
        "channel": video.get("channel_handle") or "",
    }
    return video_cfg, cross_cfg

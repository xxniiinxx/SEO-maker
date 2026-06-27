"""Build and refresh project YAML from GitHub repo and/or YouTube URLs."""

from __future__ import annotations

import re
from datetime import datetime

from src.content_enrich import enrich_social_context, pick_hashtags, pick_subreddits
from src.github_fetch import fetch_repo, repo_to_config_seed
from src.url_detect import detect_url_type
from src.youtube_fetch import (
    extract_youtube_urls_from_text,
    fetch_video,
    overview_timestamps,
    parse_channel_handle,
    setup_timestamps,
    slugify_video_id,
    video_to_config_entry,
)


def infer_playlists(niche: str, topics: list[str], repo_name: str) -> list[str]:
    playlists: list[str] = []
    niche_lower = niche.lower()
    if "solana" in niche_lower or "solana" in topics:
        playlists.append("Solana Projects")
    if "game" in niche_lower or "casino" in topics or "blockchain-game" in topics:
        playlists.append("Web3 Games")
    if "bot" in niche_lower or "trading" in niche_lower:
        playlists.append("Trading Bots")
    if repo_name:
        playlists.append(f"{repo_name.replace('-', ' ').title()} Tutorials")
    if not playlists:
        playlists = ["Project Tutorials", "Dev Walkthroughs"]
    return playlists[:4]


def infer_channel_keywords(niche: str, topics: list[str]) -> list[str]:
    keywords = [niche] if niche else []
    for topic in topics[:4]:
        label = topic.replace("-", " ").title()
        if label not in keywords:
            keywords.append(label)
    return keywords[:5]


def infer_niche_from_text(text: str, fallback: str = "Developer tutorials") -> str:
    lower = text.lower()
    checks = [
        ("solana", "Solana development tutorials"),
        ("polymarket", "Polymarket and trading tutorials"),
        ("ethereum", "Ethereum development tutorials"),
        ("web3", "Web3 developer tutorials"),
        ("crypto", "Crypto developer tutorials"),
        ("bot", "Trading bot tutorials"),
        ("tutorial", "Developer tutorials"),
    ]
    for needle, label in checks:
        if needle in lower:
            return label
    return fallback


def infer_topics_from_text(text: str) -> list[str]:
    lower = text.lower()
    candidates = [
        "solana",
        "web3",
        "tutorial",
        "typescript",
        "javascript",
        "crypto",
        "defi",
        "blockchain",
        "programming",
    ]
    return [word for word in candidates if word in lower][:6]


def apply_youtube_videos(config: dict, video_urls: list[str]) -> dict:
    github = config.get("github") or {}
    repo_name = github.get("repo_name") or config.get("project_name") or ""
    topics = github.get("topics") or []

    youtube = config.setdefault("youtube", {})
    cross = config.setdefault("cross_links", {})
    videos = youtube.setdefault("videos", [])
    cross_videos = cross.setdefault("youtube_videos", [])

    existing_urls = {v.get("youtube_url") for v in videos if v.get("youtube_url")}
    existing_ids = {v.get("id") for v in videos}

    for url in video_urls:
        url = url.strip()
        if not url:
            continue
        meta = fetch_video(url)
        if meta["url"] in existing_urls:
            continue

        video_cfg, cross_cfg = video_to_config_entry(meta, repo_name, topics)
        if video_cfg["id"] in existing_ids:
            video_cfg["id"] = f"{video_cfg['id']}-{meta['video_id'][:6]}"
            cross_cfg["id"] = video_cfg["id"]

        videos.append(video_cfg)
        cross_videos.append(cross_cfg)
        existing_urls.add(meta["url"])
        existing_ids.add(video_cfg["id"])

        handle = meta.get("channel_handle")
        if handle and not youtube.get("channel_handle"):
            youtube["channel_handle"] = handle

    return config


def apply_youtube_channel(config: dict, channel_url: str) -> dict:
    handle = parse_channel_handle(channel_url)
    if not handle.startswith("@"):
        handle = f"@{handle}"
    config.setdefault("youtube", {})["channel_handle"] = handle
    return config


def _short_video_keyword(primary_keyword: str, repo_name: str) -> str:
    human = repo_name.replace("-", " ").title()
    primary = (primary_keyword or "").strip()
    if "solana" in primary.lower():
        return f"{human} on Solana"
    if len(primary) <= 48:
        return primary
    return human[:48]


def suggest_youtube_videos_from_repo(config: dict) -> dict:
    """Create SEO-ready YouTube video templates from GitHub repo metadata."""
    youtube = config.setdefault("youtube", {})
    if youtube.get("videos"):
        return config

    github = config.get("github") or {}
    repo_name = github.get("repo_name") or config.get("project_name", "project")
    primary = github.get("primary_keyword") or repo_name.replace("-", " ")
    topics = github.get("topics") or []
    channel = youtube.get("channel_handle") or "@YourChannel"
    year = str(datetime.now().year)
    short_kw = _short_video_keyword(primary, repo_name)

    templates = [
        {
            "id": "setup-tutorial",
            "primary_keyword": f"{short_kw} tutorial",
            "video_topic": f"How to set up and run {repo_name} step by step",
            "year": year,
            "target_length_minutes": 12,
            "secondary_keywords": topics[:5],
            "timestamps": setup_timestamps(),
        },
        {
            "id": "project-overview",
            "primary_keyword": short_kw,
            "video_topic": f"{short_kw} — architecture and demo walkthrough",
            "year": year,
            "target_length_minutes": 10,
            "secondary_keywords": topics[:5],
            "timestamps": overview_timestamps(),
        },
    ]

    cross = config.setdefault("cross_links", {})
    cross_videos = cross.setdefault("youtube_videos", [])
    youtube["videos"] = templates

    for video in templates:
        cross_videos.append(
            {
                "id": video["id"],
                "title": video["video_topic"],
                "url": f"https://youtube.com/watch?v=YOUR_{video['id'].upper().replace('-', '_')}_ID",
                "channel": channel,
            }
        )

    if not youtube.get("channel_handle"):
        youtube["channel_handle"] = channel

    return config


def enrich_github_youtube(config: dict, readme_text: str = "") -> dict:
    """Attach real or suggested YouTube content to a GitHub-based config."""
    readme = readme_text or (config.get("github") or {}).get("readme_excerpt") or ""
    found_urls = extract_youtube_urls_from_text(readme)

    if found_urls:
        apply_youtube_videos(config, found_urls)
        config.setdefault("sources", {})["youtube_videos"] = found_urls

    if not (config.get("youtube") or {}).get("videos"):
        suggest_youtube_videos_from_repo(config)

    return config


def get_content_modes(config: dict) -> dict[str, bool]:
    """Decide which output packs to generate from config/sources."""
    sources = config.get("sources") or {}
    github = config.get("github") or {}
    youtube = config.get("youtube") or {}

    has_github = bool(sources.get("github_repo") or github.get("repo_url"))
    has_youtube = bool(
        sources.get("youtube_videos")
        or sources.get("youtube_channel")
        or youtube.get("videos")
        or youtube.get("channel_handle")
    )
    mode = sources.get("mode")
    if mode == "youtube":
        has_github = False

    return {
        "github": has_github,
        "youtube": has_youtube,
        "social": config.get("social", {}).get("enabled", True) is not False,
    }


def build_config_from_youtube(
    youtube_video_urls: list[str] | None = None,
    youtube_channel_url: str | None = None,
    niche: str = "",
) -> dict:
    video_urls = [u.strip() for u in (youtube_video_urls or []) if u.strip()]
    if not video_urls and not youtube_channel_url:
        raise ValueError("Provide at least one YouTube video URL or channel URL")

    project_name = "youtube-project"
    if video_urls:
        meta = fetch_video(video_urls[0])
        project_name = slugify_video_id(meta["title"], meta["video_id"])
    elif youtube_channel_url:
        handle = parse_channel_handle(youtube_channel_url)
        project_name = handle.lstrip("@").replace(" ", "-").lower() or "youtube-channel"

    seed_text = video_urls[0] if video_urls else youtube_channel_url or ""
    inferred_niche = niche or infer_niche_from_text(seed_text)
    topics = infer_topics_from_text(seed_text)

    config = {
        "project_name": project_name,
        "niche": inferred_niche,
        "github": {
            "repo_url": "",
            "repo_name": project_name,
            "primary_keyword": "",
            "short_description": "",
            "topics": topics,
            "features": [],
            "tech_stack": [],
            "use_cases": [],
            "license": "MIT",
            "language": "",
        },
        "youtube": {
            "channel_handle": "",
            "playlists": [],
            "videos": [],
            "channel_about_keywords": [],
        },
        "cross_links": {
            "website": "",
            "related_repos": [],
            "youtube_videos": [],
        },
        "social": {
            "enabled": True,
            "hashtags": [],
            "subreddits": pick_subreddits(topics, inferred_niche),
        },
        "sources": {
            "mode": "youtube",
            "youtube_videos": video_urls,
        },
    }
    if youtube_channel_url:
        config["sources"]["youtube_channel"] = youtube_channel_url.strip()

    if youtube_channel_url:
        apply_youtube_channel(config, youtube_channel_url)
    if video_urls:
        apply_youtube_videos(config, video_urls)

    youtube = config["youtube"]
    first_video = (youtube.get("videos") or [None])[0]
    github = config["github"]
    if first_video:
        github["primary_keyword"] = first_video["primary_keyword"]
        github["short_description"] = first_video["video_topic"]
        github["features"] = [
            f"Video tutorial: {first_video['video_topic']}",
            f"Primary keyword focus: {first_video['primary_keyword']}",
        ]
        github["use_cases"] = [
            f"Learn from the walkthrough: {first_video['primary_keyword']}",
            "Apply the techniques shown in your own projects",
        ]

    if not youtube.get("playlists"):
        youtube["playlists"] = infer_playlists(inferred_niche, topics, project_name)
    if not youtube.get("channel_about_keywords"):
        youtube["channel_about_keywords"] = infer_channel_keywords(inferred_niche, topics)
    if not config["social"].get("hashtags") and topics:
        config["social"]["hashtags"] = pick_hashtags(topics, github.get("primary_keyword") or project_name)

    return finalize_config(config)


def auto_build_config(
    repo_url: str | None = None,
    youtube_video_urls: list[str] | None = None,
    youtube_channel_url: str | None = None,
    niche: str = "",
    github_token: str | None = None,
) -> dict:
    repo_url = (repo_url or "").strip()
    video_urls = [u.strip() for u in (youtube_video_urls or []) if u.strip()]

    if not repo_url and not video_urls and not youtube_channel_url:
        raise ValueError("Provide a GitHub repo URL and/or a YouTube video/channel URL")

    if repo_url and not video_urls and not youtube_channel_url:
        config = _build_github_config(repo_url, niche, github_token)
        config["sources"]["mode"] = "github"
        return config

    if not repo_url and (video_urls or youtube_channel_url):
        return build_config_from_youtube(video_urls, youtube_channel_url, niche)

    config = _build_github_config(repo_url, niche, github_token)
    config["sources"]["mode"] = "both"
    config["sources"]["youtube_videos"] = video_urls
    if youtube_channel_url:
        config["sources"]["youtube_channel"] = youtube_channel_url.strip()
        apply_youtube_channel(config, youtube_channel_url)
    if video_urls:
        apply_youtube_videos(config, video_urls)
    return finalize_config(config)


def _build_github_config(repo_url: str, niche: str, github_token: str | None) -> dict:
    repo = fetch_repo(repo_url, token=github_token)
    config = repo_to_config_seed(repo, niche=niche)
    config["sources"] = {
        "github_repo": repo_url,
        "youtube_videos": [],
    }
    youtube = config.setdefault("youtube", {})
    github = config.get("github") or {}
    topics = github.get("topics") or []
    inferred_niche = config.get("niche") or ""

    if not youtube.get("playlists"):
        youtube["playlists"] = infer_playlists(
            inferred_niche, topics, config.get("project_name", "")
        )
    if not youtube.get("channel_about_keywords"):
        youtube["channel_about_keywords"] = infer_channel_keywords(inferred_niche, topics)

    enrich_github_youtube(config, repo.get("readme_full") or "")
    return finalize_config(config)


def parse_input_urls(
    url: str | None = None,
    repo: str | None = None,
    youtube: list[str] | None = None,
    channel: str | None = None,
) -> tuple[str | None, list[str], str | None]:
    """Normalize CLI positional URL and flags into repo + youtube lists."""
    repo_url = (repo or "").strip()
    video_urls = [u.strip() for u in (youtube or []) if u.strip()]
    channel_url = (channel or "").strip()

    if url:
        url = url.strip()
        kind = detect_url_type(url)
        if kind == "github":
            if repo_url and repo_url != url:
                raise ValueError("Conflicting GitHub URLs in positional URL and --repo")
            repo_url = url
        elif kind == "youtube_video":
            if url not in video_urls:
                video_urls.append(url)
        else:
            if channel_url and channel_url != url:
                raise ValueError("Conflicting channel URLs in positional URL and --channel")
            channel_url = url

    return repo_url or None, video_urls, channel_url or None


def refresh_config_from_sources(config: dict, github_token: str | None = None) -> dict:
    """Re-fetch metadata using URLs stored in config.sources."""
    sources = config.get("sources") or {}
    github = config.get("github") or {}
    repo_url = sources.get("github_repo") or github.get("repo_url") or None
    video_urls = sources.get("youtube_videos") or [
        v["youtube_url"]
        for v in (config.get("youtube") or {}).get("videos") or []
        if v.get("youtube_url")
    ]
    channel_url = sources.get("youtube_channel") or ""

    old_cross = config.get("cross_links") or {}
    preserved = {
        "related_repos": old_cross.get("related_repos") or [],
        "website": old_cross.get("website") or "",
    }

    if repo_url and (video_urls or channel_url):
        rebuilt = auto_build_config(repo_url, video_urls, channel_url or None, config.get("niche") or "", github_token)
    elif repo_url:
        rebuilt = auto_build_config(repo_url=repo_url, niche=config.get("niche") or "", github_token=github_token)
    elif video_urls or channel_url:
        rebuilt = build_config_from_youtube(video_urls, channel_url or None, config.get("niche") or "")
    else:
        raise ValueError("No github_repo or youtube URLs in config.sources")

    new_cross = rebuilt.get("cross_links") or {}
    if preserved["related_repos"]:
        new_cross["related_repos"] = preserved["related_repos"]
    if preserved["website"]:
        new_cross["website"] = preserved["website"]

    return rebuilt


def finalize_config(config: dict) -> dict:
    """Apply enrichment so saved YAML contains inferred fields."""
    enriched = enrich_social_context(config)
    config["niche"] = enriched.get("niche", config.get("niche"))
    config["github"] = enriched.get("github", config.get("github"))
    config["social"] = enriched.get("social", config.get("social"))
    return config

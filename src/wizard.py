"""Interactive config wizard — prompts for SEO fields after GitHub repo URL."""

from __future__ import annotations

import yaml

from src.config_builder import (
    apply_youtube_channel,
    apply_youtube_videos,
    finalize_config,
    infer_channel_keywords,
    infer_playlists,
)
from src.github_fetch import fetch_repo, repo_to_config_seed


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def _prompt_list(label: str, defaults: list[str] | None = None) -> list[str]:
    defaults = defaults or []
    print(f"{label} (comma-separated, Enter to keep defaults)")
    if defaults:
        print(f"  default: {', '.join(defaults)}")
    raw = input("> ").strip()
    if not raw:
        return defaults
    return [item.strip() for item in raw.split(",") if item.strip()]


def _prompt_yes_no(label: str, default: bool = True) -> bool:
    default_char = "Y/n" if default else "y/N"
    raw = input(f"{label} ({default_char}): ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "1", "true")


def run_wizard(
    repo_url: str,
    token: str | None = None,
    youtube_urls: list[str] | None = None,
    channel_url: str | None = None,
) -> dict:
    print(f"\nFetching {repo_url} ...")
    repo = fetch_repo(repo_url, token=token)
    config = repo_to_config_seed(repo)
    config["sources"] = {
        "github_repo": repo_url.strip(),
        "youtube_videos": [u.strip() for u in (youtube_urls or []) if u.strip()],
    }
    if channel_url:
        config["sources"]["youtube_channel"] = channel_url.strip()

    print(f"\nFound: {repo['repo_name']} — {repo['description'] or '(no description)'}")
    config["niche"] = _prompt("Niche / market (e.g. Polymarket trading bots)", config["niche"])

    github = config["github"]
    github["primary_keyword"] = _prompt("Primary SEO keyword", github["primary_keyword"])
    github["short_description"] = _prompt("GitHub About / short description", github["short_description"])
    github["topics"] = _prompt_list("GitHub topics (5–10)", github["topics"])
    github["features"] = _prompt_list("Key features (3–6)", github.get("features") or [])
    github["tech_stack"] = _prompt_list(
        "Tech stack",
        github.get("tech_stack") or ([repo["language"]] if repo["language"] else []),
    )
    github["use_cases"] = _prompt_list("Use cases (2–4)", github.get("use_cases") or [])

    youtube = config["youtube"]
    if channel_url:
        apply_youtube_channel(config, channel_url)
    youtube["channel_handle"] = _prompt(
        "YouTube channel handle (e.g. @YourChannel)", youtube.get("channel_handle", "")
    )
    youtube["channel_about_keywords"] = _prompt_list(
        "Channel About keywords (3–5)",
        infer_channel_keywords(config["niche"], github["topics"]),
    )
    youtube["playlists"] = _prompt_list(
        "YouTube playlists (2–4)",
        infer_playlists(config["niche"], github["topics"], config["project_name"]),
    )

    if youtube_urls:
        apply_youtube_videos(config, youtube_urls)
        print(f"Added {len(youtube_urls)} YouTube video(s) from URLs.")
    elif _prompt_yes_no("Add a YouTube video manually?", default=False):
        video_url = _prompt("YouTube video URL")
        if video_url:
            apply_youtube_videos(config, [video_url])
            config["sources"]["youtube_videos"] = [video_url.strip()]
    elif _prompt_yes_no("Add a YouTube video template (no URL)?", default=True):
        video_id = _prompt("Video slug (folder name)", "setup-tutorial")
        video = {
            "id": video_id,
            "primary_keyword": _prompt("Video primary keyword", f"{github['primary_keyword']} tutorial"),
            "video_topic": _prompt("Video topic / angle", f"How to set up {github['repo_name']}"),
            "year": _prompt("Year in title", "2026"),
            "target_length_minutes": 12,
            "timestamps": [
                "0:00 Intro and disclaimer",
                "1:30 Prerequisites",
                "4:00 Clone and install",
                "6:30 Configuration",
                "9:00 Demo",
                "11:00 GitHub link and next steps",
            ],
            "secondary_keywords": github["topics"][:5],
        }
        youtube.setdefault("videos", []).append(video)

    cross = config["cross_links"]
    cross["website"] = _prompt("Project website / hub URL", cross.get("website", ""))
    if _prompt_yes_no("Add related GitHub repos for cross-linking?", default=False):
        name = _prompt("Related repo name")
        url = _prompt("Related repo URL")
        if name and url:
            cross["related_repos"] = [{"name": name, "url": url}]

    social = config["social"]
    social["hashtags"] = _prompt_list(
        "Social hashtags (no #)",
        social.get("hashtags") or [t.replace("-", "") for t in github["topics"][:4]],
    )
    social["subreddits"] = _prompt_list(
        "Target subreddits",
        social.get("subreddits") or ["r/opensource", "r/programming"],
    )

    return finalize_config(config)


def save_config(config: dict, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = dict(config)
    for key in (
        "devto_tags",
        "devto_title",
        "setup_steps",
        "architecture_points",
        "cover_image_hint",
    ):
        cleaned.pop(key, None)
    github = cleaned.get("github")
    if isinstance(github, dict):
        github.pop("readme_full", None)
        excerpt = github.get("readme_excerpt") or ""
        if len(excerpt) > 800:
            github["readme_excerpt"] = excerpt[:800] + "..."
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(cleaned, handle, sort_keys=False, allow_unicode=True, default_flow_style=False)

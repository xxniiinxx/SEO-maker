"""Interactive config wizard — prompts for SEO fields after GitHub repo URL."""

from __future__ import annotations

import yaml

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


def run_wizard(repo_url: str, token: str | None = None) -> dict:
    print(f"\nFetching {repo_url} ...")
    repo = fetch_repo(repo_url, token=token)
    config = repo_to_config_seed(repo)

    print(f"\nFound: {repo['repo_name']} — {repo['description'] or '(no description)'}")
    config["niche"] = _prompt("Niche / market (e.g. Polymarket trading bots)", config["niche"])

    github = config["github"]
    github["primary_keyword"] = _prompt("Primary SEO keyword", github["primary_keyword"])
    github["short_description"] = _prompt("GitHub About / short description", github["short_description"])
    github["topics"] = _prompt_list("GitHub topics (5–10)", github["topics"])
    github["features"] = _prompt_list("Key features (3–6)")
    github["tech_stack"] = _prompt_list(
        "Tech stack",
        github["tech_stack"] or ([repo["language"]] if repo["language"] else []),
    )
    github["use_cases"] = _prompt_list("Use cases (2–4)")

    youtube = config["youtube"]
    youtube["channel_handle"] = _prompt("YouTube channel handle (e.g. @YourChannel)")
    youtube["channel_about_keywords"] = _prompt_list("Channel About keywords (3–5)")
    youtube["playlists"] = _prompt_list("YouTube playlists (2–4)")

    if _prompt_yes_no("Add a YouTube video template?", default=True):
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
        youtube["videos"] = [video]

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
        [t.replace("-", "") for t in github["topics"][:4]],
    )
    social["subreddits"] = _prompt_list(
        "Target subreddits",
        ["r/opensource", "r/programming"],
    )

    return config


def save_config(config: dict, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False, allow_unicode=True)

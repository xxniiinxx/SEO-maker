from pathlib import Path

from src.content_enrich import enrich_social_context
from src.github_fetch import fetch_repo
from src.render import render
from src.rules import validate_social


def _load_readme_excerpt(config: dict) -> str:
    github = config.get("github") or {}
    excerpt = github.get("readme_excerpt") or ""
    if excerpt or not github.get("repo_url"):
        return excerpt
    try:
        repo = fetch_repo(github["repo_url"])
        return repo.get("readme_excerpt") or ""
    except Exception:
        return ""


def generate_social_pack(config: dict, output_dir: Path) -> list[str]:
    social = config.get("social") or {}
    if social.get("enabled") is False:
        return []

    out = output_dir / "social"
    out.mkdir(parents=True, exist_ok=True)

    readme_excerpt = _load_readme_excerpt(config)
    enriched = enrich_social_context(config, readme_excerpt)

    ctx = {
        "config": enriched,
        "github": enriched.get("github") or {},
        "youtube": enriched.get("youtube") or {},
        "cross_links": enriched.get("cross_links") or {},
        "social": enriched.get("social") or {},
        "project_name": enriched.get("project_name", ""),
        "niche": enriched.get("niche", ""),
        "devto_tags": enriched.get("devto_tags") or [],
        "devto_title": enriched.get("devto_title") or "",
        "setup_steps": enriched.get("setup_steps") or [],
        "architecture_points": enriched.get("architecture_points") or [],
        "cover_image_hint": enriched.get("cover_image_hint") or "",
        "is_video_only": enriched.get("is_video_only", False),
        "primary_video_url": enriched.get("primary_video_url") or "",
    }

    warnings = validate_social(enriched)

    files = {
        "devto-post.md": "social/devto-post.md.j2",
        "medium-post.md": "social/medium-post.md.j2",
        "x-post-thread.txt": "social/x-post-thread.txt.j2",
        "reddit-post.txt": "social/reddit-post.txt.j2",
        "linkedin-post.txt": "social/linkedin-post.txt.j2",
        "discord-announcement.txt": "social/discord-announcement.txt.j2",
        "promotion-checklist.txt": "social/promotion-checklist.txt.j2",
    }

    for filename, template in files.items():
        (out / filename).write_text(render(template, **ctx), encoding="utf-8")

    if warnings:
        (out / "warnings.txt").write_text("\n".join(warnings) + "\n", encoding="utf-8")

    return warnings

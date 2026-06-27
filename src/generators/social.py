from pathlib import Path

from src.render import render


def generate_social_pack(config: dict, output_dir: Path) -> list[str]:
    social = config.get("social") or {}
    if social.get("enabled") is False:
        return []

    out = output_dir / "social"
    out.mkdir(parents=True, exist_ok=True)

    ctx = {
        "config": config,
        "github": config.get("github") or {},
        "youtube": config.get("youtube") or {},
        "cross_links": config.get("cross_links") or {},
        "social": social,
        "project_name": config.get("project_name", ""),
        "niche": config.get("niche", ""),
    }

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

    return []

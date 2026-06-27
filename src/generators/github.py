from pathlib import Path

from src.render import render
from src.rules import validate_github


def generate_github_pack(config: dict, output_dir: Path) -> list[str]:
    github = config.get("github") or {}
    warnings = validate_github(github)
    out = output_dir / "github"
    out.mkdir(parents=True, exist_ok=True)

    ctx = {
        "config": config,
        "github": github,
        "cross_links": config.get("cross_links") or {},
        "youtube": config.get("youtube") or {},
        "social": config.get("social") or {},
        "project_name": config.get("project_name", ""),
        "niche": config.get("niche", ""),
    }

    files = {
        "about.txt": "github/about.txt.j2",
        "topics.txt": "github/topics.txt.j2",
        "readme-seo.md": "github/readme-seo.md.j2",
        "readme-seo-sections.md": "github/readme-seo-sections.md.j2",
        "repo-name-suggestion.txt": "github/repo-name-suggestion.txt.j2",
    }

    for filename, template in files.items():
        (out / filename).write_text(render(template, **ctx), encoding="utf-8")

    if warnings:
        (output_dir / "github" / "warnings.txt").write_text("\n".join(warnings) + "\n", encoding="utf-8")

    return warnings

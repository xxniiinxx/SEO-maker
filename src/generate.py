"""SEO-maker CLI — generate GitHub, YouTube, and social SEO packs from project config."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

from src.config_builder import (
    auto_build_config,
    get_content_modes,
    parse_input_urls,
    refresh_config_from_sources,
)
from src.generators.github import generate_github_pack
from src.generators.social import generate_social_pack
from src.generators.youtube import generate_youtube_pack
from src.rules import validate_github, validate_youtube_video
from src.wizard import run_wizard, save_config

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECTS_DIR = ROOT / "config" / "projects"
DEFAULT_OUTPUT_DIR = ROOT / "output"
EXAMPLE_CONFIG = ROOT / "config" / "projects" / "example.yaml"


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {path}")
    return data


def validate_config(config: dict) -> list[str]:
    warnings: list[str] = []
    modes = get_content_modes(config)

    if modes["github"]:
        github = config.get("github")
        if not github:
            warnings.append("WARNING: Missing 'github' section.")
        else:
            warnings.extend(validate_github(github))

    if modes["youtube"]:
        youtube = config.get("youtube") or {}
        for video in youtube.get("videos") or []:
            video_id = video.get("id", "unknown")
            warnings.extend(validate_youtube_video(video, video_id, config))

    return warnings


def write_validation_report(output_dir: Path, warnings: list[str]) -> None:
    errors = [w for w in warnings if w.startswith("ERROR")]
    report = [
        "SEO guide validation report",
        "================================",
        "",
    ]
    if warnings:
        report.extend(warnings)
    else:
        report.append("All checks passed.")
    report.extend(
        [
            "",
            f"Summary: {len(errors)} error(s), {len(warnings) - len(errors)} warning(s)",
        ]
    )
    (output_dir / "validation-report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")


def generate_all(config: dict, output_dir: Path) -> list[str]:
    warnings: list[str] = []
    modes = get_content_modes(config)
    output_dir.mkdir(parents=True, exist_ok=True)

    for pack in ("github", "youtube"):
        if not modes.get(pack) and (output_dir / pack).exists():
            shutil.rmtree(output_dir / pack)

    if modes["github"]:
        warnings.extend(generate_github_pack(config, output_dir))
    if modes["youtube"]:
        warnings.extend(generate_youtube_pack(config, output_dir))
    if modes["social"]:
        warnings.extend(generate_social_pack(config, output_dir))

    write_validation_report(output_dir, warnings)
    return warnings


def cmd_validate(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    warnings = validate_config(config)
    print(f"Validation for {Path(args.config).name}:")
    if warnings:
        for line in warnings:
            print(f"  {line}")
        return 1
    print("  OK: no warnings")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config = load_config(config_path)

    if args.refresh:
        print("Refreshing config from GitHub/YouTube sources ...")
        config = refresh_config_from_sources(config, github_token=args.token)
        save_config(config, config_path)
        print(f"Updated config: {config_path}")

    project_name = config.get("project_name") or config_path.stem
    output_dir = Path(args.output) / project_name
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings = generate_all(config, output_dir)
    print(f"Generated SEO pack: {output_dir}")
    for sub in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        print(f"  {sub.relative_to(output_dir)}")

    if warnings:
        print("\nWarnings (also saved to validation-report.txt):")
        for line in warnings:
            print(f"  {line}")
    return 0


def cmd_list_projects(_: argparse.Namespace) -> int:
    if not DEFAULT_PROJECTS_DIR.is_dir():
        print(f"No projects directory: {DEFAULT_PROJECTS_DIR}")
        return 1
    configs = sorted(DEFAULT_PROJECTS_DIR.glob("*.yaml"))
    if not configs:
        print("No project configs found in config/projects/")
        return 1
    print("Project configs:")
    for path in configs:
        print(f"  {path.name}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    name = args.name.strip()
    if not name:
        print("Project name required.")
        return 1

    dest = DEFAULT_PROJECTS_DIR / f"{name}.yaml"
    if dest.exists() and not args.force:
        print(f"Already exists: {dest} (use --force to overwrite)")
        return 1

    if not EXAMPLE_CONFIG.is_file():
        print(f"Missing template: {EXAMPLE_CONFIG}")
        return 1

    text = EXAMPLE_CONFIG.read_text(encoding="utf-8")
    text = text.replace("project_name: pm-copy-trader", f"project_name: {name}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    print(f"Created: {dest}")
    print(f"Edit the file, then run: python -m src.generate generate config/projects/{name}.yaml")
    return 0


def cmd_wizard(args: argparse.Namespace) -> int:
    try:
        repo_url, video_urls, channel_url = parse_input_urls(
            url=args.url,
            repo=args.repo,
            youtube=args.youtube,
            channel=args.channel,
        )
    except ValueError as exc:
        print(exc)
        return 1

    if not repo_url and not video_urls and not channel_url:
        print("Provide a GitHub repo URL or YouTube video/channel URL.")
        return 1

    if repo_url and not video_urls and not channel_url:
        config = run_wizard(repo_url, token=args.token)
    elif not repo_url:
        from src.config_builder import build_config_from_youtube, finalize_config

        config = build_config_from_youtube(video_urls, channel_url, args.niche or "")
        print("\nAuto-filled from YouTube.")
        niche = input(f"Niche [{config['niche']}]: ").strip()
        if niche:
            config["niche"] = niche
        config = finalize_config(config)
    else:
        config = run_wizard(
            repo_url,
            token=args.token,
            youtube_urls=video_urls,
            channel_url=channel_url,
        )
    name = config.get("project_name") or "project"
    dest = Path(args.output) if args.output else DEFAULT_PROJECTS_DIR / f"{name}.yaml"

    if dest.is_dir() or str(dest).endswith(("/", "\\")):
        dest = dest / f"{name}.yaml"

    if dest.exists() and not args.force:
        print(f"Already exists: {dest} (use --force to overwrite)")
        return 1

    save_config(config, dest)
    print(f"\nSaved config: {dest}")

    if args.generate:
        output_dir = DEFAULT_OUTPUT_DIR / name
        warnings = generate_all(config, output_dir)
        print(f"Generated SEO pack: {output_dir}")
        if warnings:
            print("\nWarnings:")
            for line in warnings:
                print(f"  {line}")
    else:
        print(f"Run: python -m src.generate generate {dest}")

    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    try:
        repo_url, video_urls, channel_url = parse_input_urls(
            url=args.url,
            repo=args.repo,
            youtube=args.youtube,
            channel=args.channel,
        )
    except ValueError as exc:
        print(exc)
        return 1

    if not repo_url and not video_urls and not channel_url:
        print("Provide a GitHub repo URL or YouTube video/channel URL.")
        print("Examples:")
        print("  python -m src.generate auto https://github.com/owner/repo -g")
        print("  python -m src.generate auto https://www.youtube.com/watch?v=VIDEO_ID -g")
        return 1

    if repo_url:
        print(f"GitHub repo: {repo_url}")
    if video_urls:
        print(f"YouTube videos: {len(video_urls)}")
    if channel_url:
        print(f"YouTube channel: {channel_url}")

    config = auto_build_config(
        repo_url=repo_url,
        youtube_video_urls=video_urls,
        youtube_channel_url=channel_url,
        niche=args.niche or "",
        github_token=args.token,
    )

    modes = get_content_modes(config)
    print(
        "Content packs: "
        + ", ".join(name for name, enabled in modes.items() if enabled)
    )

    name = config["project_name"]
    dest = Path(args.output) if args.output else DEFAULT_PROJECTS_DIR / f"{name}.yaml"
    if dest.is_dir():
        dest = dest / f"{name}.yaml"

    if dest.exists() and not args.force:
        print(f"Already exists: {dest} (use --force to overwrite)")
        return 1

    save_config(config, dest)
    print(f"Saved config: {dest}")

    if args.generate:
        output_dir = DEFAULT_OUTPUT_DIR / name
        warnings = generate_all(config, output_dir)
        print(f"Generated SEO pack: {output_dir}")
        if warnings:
            print("\nWarnings:")
            for line in warnings:
                print(f"  {line}")
    else:
        print(f"Run: python -m src.generate generate {dest}")

    return 0


def cmd_from_repo(args: argparse.Namespace) -> int:
    """Legacy alias for auto-build from GitHub (+ optional YouTube URLs)."""
    return cmd_auto(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seo-maker",
        description="Generate SEO-optimized GitHub, YouTube, and social content from project config.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate SEO pack for a project config")
    gen.add_argument("config", help="Path to project YAML (e.g. config/projects/example.yaml)")
    gen.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT_DIR), help="Output root directory")
    gen.add_argument(
        "--refresh",
        action="store_true",
        help="Re-fetch GitHub/YouTube metadata into config before generating",
    )
    gen.add_argument("--token", help="GitHub API token (optional, for refresh rate limits)")
    gen.set_defaults(func=cmd_generate)

    val = sub.add_parser("validate", help="Validate config against SEO rules")
    val.add_argument("config", help="Path to project YAML")
    val.set_defaults(func=cmd_validate)

    sub.add_parser("list", help="List project configs").set_defaults(func=cmd_list_projects)

    init = sub.add_parser("init", help="Create a new project config from example")
    init.add_argument("name", help="Project slug (filename without .yaml)")
    init.add_argument("-f", "--force", action="store_true", help="Overwrite if exists")
    init.set_defaults(func=cmd_init)

    wiz = sub.add_parser("wizard", help="Interactive config from GitHub and/or YouTube URL")
    wiz.add_argument("url", nargs="?", help="GitHub repo or YouTube video/channel URL")
    wiz.add_argument("--repo", help="GitHub repository URL")
    wiz.add_argument("-o", "--output", help="Save config path (default: config/projects/<name>.yaml)")
    wiz.add_argument("-g", "--generate", action="store_true", help="Generate SEO pack after wizard")
    wiz.add_argument("-f", "--force", action="store_true", help="Overwrite existing config")
    wiz.add_argument("--token", help="GitHub API token (optional, for rate limits)")
    wiz.add_argument("--youtube", action="append", help="YouTube video URL (repeatable)")
    wiz.add_argument("--channel", help="YouTube channel URL (e.g. https://youtube.com/@handle)")
    wiz.add_argument("--niche", help="Override niche string")
    wiz.set_defaults(func=cmd_wizard)

    auto = sub.add_parser(
        "auto",
        help="Auto-build YAML from GitHub repo and/or YouTube URL (provide at least one)",
    )
    auto.add_argument("url", nargs="?", help="GitHub repo or YouTube video/channel URL")
    auto.add_argument("--repo", help="GitHub repository URL")
    auto.add_argument("--youtube", action="append", help="YouTube video URL (repeatable)")
    auto.add_argument("--channel", help="YouTube channel URL")
    auto.add_argument("--niche", help="Override niche string")
    auto.add_argument("-o", "--output", help="Save config path (default: config/projects/<name>.yaml)")
    auto.add_argument("-g", "--generate", action="store_true", help="Generate SEO pack after saving config")
    auto.add_argument("-f", "--force", action="store_true", help="Overwrite existing config")
    auto.add_argument("--token", help="GitHub API token (optional)")
    auto.set_defaults(func=cmd_auto)

    fr = sub.add_parser("from-repo", help="Alias for auto with --repo")
    fr.add_argument("url", nargs="?", help="GitHub repo URL (or use --repo)")
    fr.add_argument("--repo", help="GitHub repository URL")
    fr.add_argument("--youtube", action="append", help="YouTube video URL (repeatable)")
    fr.add_argument("--channel", help="YouTube channel URL")
    fr.add_argument("--niche", help="Override niche string")
    fr.add_argument("-g", "--generate", action="store_true", help="Generate after saving")
    fr.add_argument("-f", "--force", action="store_true", help="Overwrite existing config")
    fr.add_argument("--token", help="GitHub API token (optional)")
    fr.set_defaults(func=cmd_from_repo)

    return parser


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

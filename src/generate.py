"""SEO-maker CLI — generate GitHub, YouTube, and social SEO packs from project config."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from src.generators.github import generate_github_pack
from src.generators.social import generate_social_pack
from src.generators.youtube import generate_youtube_pack
from src.github_fetch import fetch_repo, repo_to_config_seed
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
    github = config.get("github")
    if not github:
        warnings.append("WARNING: Missing 'github' section.")
    else:
        warnings.extend(validate_github(github))

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
    warnings.extend(generate_github_pack(config, output_dir))
    warnings.extend(generate_youtube_pack(config, output_dir))
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
    repo_url = args.repo_url.strip()
    if not repo_url:
        print("GitHub repo URL required.")
        return 1

    config = run_wizard(repo_url, token=args.token)
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


def cmd_from_repo(args: argparse.Namespace) -> int:
    repo_url = args.repo_url.strip()
    print(f"Fetching {repo_url} ...")
    repo = fetch_repo(repo_url, token=args.token)
    config = repo_to_config_seed(repo, niche=args.niche or "")

    if EXAMPLE_CONFIG.is_file():
        example = load_config(EXAMPLE_CONFIG)
        for key in ("youtube", "cross_links", "social"):
            if key in example and not config.get(key):
                config[key] = example[key]

    name = config["project_name"]
    dest = DEFAULT_PROJECTS_DIR / f"{name}.yaml"
    if dest.exists() and not args.force:
        print(f"Config exists: {dest} — use --force or run wizard for interactive fill-in")
        config = load_config(dest)
    else:
        save_config(config, dest)
        print(f"Seeded config: {dest}")
        print("Edit the YAML to complete SEO fields, or run: python -m src.generate wizard", repo_url)

    if args.generate:
        output_dir = DEFAULT_OUTPUT_DIR / name
        generate_all(config, output_dir)
        print(f"Generated: {output_dir}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seo-maker",
        description="Generate SEO-optimized GitHub, YouTube, and social content from project config.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate SEO pack for a project config")
    gen.add_argument("config", help="Path to project YAML (e.g. config/projects/example.yaml)")
    gen.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT_DIR), help="Output root directory")
    gen.set_defaults(func=cmd_generate)

    val = sub.add_parser("validate", help="Validate config against SEO rules")
    val.add_argument("config", help="Path to project YAML")
    val.set_defaults(func=cmd_validate)

    sub.add_parser("list", help="List project configs").set_defaults(func=cmd_list_projects)

    init = sub.add_parser("init", help="Create a new project config from example")
    init.add_argument("name", help="Project slug (filename without .yaml)")
    init.add_argument("-f", "--force", action="store_true", help="Overwrite if exists")
    init.set_defaults(func=cmd_init)

    wiz = sub.add_parser("wizard", help="Interactive config from GitHub repo URL")
    wiz.add_argument("repo_url", help="GitHub repository URL")
    wiz.add_argument("-o", "--output", help="Save config path (default: config/projects/<repo>.yaml)")
    wiz.add_argument("-g", "--generate", action="store_true", help="Generate SEO pack after wizard")
    wiz.add_argument("-f", "--force", action="store_true", help="Overwrite existing config")
    wiz.add_argument("--token", help="GitHub API token (optional, for rate limits)")
    wiz.set_defaults(func=cmd_wizard)

    fr = sub.add_parser("from-repo", help="Seed config from GitHub repo metadata")
    fr.add_argument("repo_url", help="GitHub repository URL")
    fr.add_argument("--niche", help="Override niche string")
    fr.add_argument("-g", "--generate", action="store_true", help="Generate after seeding")
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

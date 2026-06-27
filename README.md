# SEO-maker

Generate SEO-optimized content packs for **GitHub repositories**, **YouTube channels**, and **social promotion** — driven by the rules in [`GUIDEs/GUIDE-1.md`](GUIDEs/GUIDE-1.md).

## What it generates

| Platform | Output files |
|----------|--------------|
| **GitHub** | `about.txt`, `topics.txt`, `readme-seo.md`, `readme-seo-sections.md`, repo name suggestions |
| **YouTube** | Channel about, playlists, per-video titles/tags/descriptions/end screens |
| **Social** | dev.to post, Medium post, X thread, Reddit post, LinkedIn, Discord, promotion checklist |
| **Validation** | `validation-report.txt` with GUIDE-based warnings |

All files land under `output/<project_name>/`.

## Quick start

```powershell
cd C:\Wip\Project\SEO-maker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Option A — Interactive wizard (recommended)

Provide your GitHub repo URL; the wizard fetches metadata and prompts for SEO fields:

```powershell
python -m src.generate wizard https://github.com/owner/your-repo -g
```

`-g` generates the full SEO pack immediately after saving config.

### Option B — Edit YAML config manually

```powershell
python -m src.generate init my-project
# edit config/projects/my-project.yaml
python -m src.generate generate config/projects/my-project.yaml
```

### Option C — Auto-seed from GitHub URL

```powershell
python -m src.generate from-repo https://github.com/owner/your-repo -g
```

Fetches repo description, topics, and language; merges with `example.yaml` structure. Edit the YAML before publishing.

## Commands

| Command | Description |
|---------|-------------|
| `wizard <repo-url> [-g]` | Interactive config + optional generate |
| `from-repo <repo-url> [-g]` | Seed config from GitHub API |
| `generate <config.yaml>` | Generate full SEO pack |
| `validate <config.yaml>` | Check config against GUIDE rules |
| `init <name>` | Copy example config for a new project |
| `list` | List configs in `config/projects/` |

## Config overview

Each project is a YAML file in `config/projects/`. Key sections:

- **`github`** — repo URL, primary keyword, about text, topics, features, tech stack
- **`youtube`** — channel handle, playlists, video definitions (keywords, timestamps)
- **`cross_links`** — website, related repos, YouTube URLs for README embeds
- **`social`** — hashtags, target subreddits

See [`config/projects/example.yaml`](config/projects/example.yaml) for a full reference (pm-copy-trader sample).

## SEO rules (from GUIDEs)

The validator enforces guidelines from GUIDE-1:

- GitHub About ≤ ~350 chars; 5–10 topics; primary keyword in About
- YouTube titles ≤ 70 chars; description lead ≤ 150 chars; 10–15 tags; timestamps recommended
- Cross-link GitHub ↔ YouTube ↔ social posts for backlinks

## Workflow

1. **Phase 1** — Paste GitHub `about.txt`, topics, README sections; update YouTube channel About
2. **Phase 2** — Upload videos using generated titles/descriptions/tags
3. **Phase 3** — Publish dev.to, Medium, X, Reddit, LinkedIn from `output/.../social/`
4. **Phase 4** — Use `validation-report.txt` and analytics to iterate

Use `social/promotion-checklist.txt` as a copy-paste checklist.

## Optional: GitHub API token

Public repos work without auth. For higher rate limits:

```powershell
$env:GITHUB_TOKEN = "ghp_..."
python -m src.generate wizard https://github.com/owner/repo --token $env:GITHUB_TOKEN
```

## Project layout

```
config/projects/     # YAML configs per repo/project
templates/           # Jinja2 templates (github/, youtube/, social/)
src/                 # CLI, rules, generators, GitHub fetch, wizard
output/              # Generated SEO packs (gitignored content OK)
GUIDEs/              # SEO strategy references
```

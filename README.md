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

### Option A — Fully automatic (provide one or both URLs)

Give **either** a GitHub repo **or** a YouTube video URL (or both). SEO-maker detects the URL type and generates only the relevant packs:

```powershell
# GitHub repo only → github/ + social/
python -m src.generate auto https://github.com/owner/your-repo -g -f

# YouTube video only → youtube/ + social/
python -m src.generate auto "https://www.youtube.com/watch?v=VIDEO_ID" -g -f

# Both (optional)
python -m src.generate auto https://github.com/owner/repo `
  --youtube "https://www.youtube.com/watch?v=VIDEO_ID" -g -f
```

`-g` generates output; `-f` overwrites an existing config.

### Option B — Interactive wizard

Prompts for extra fields after fetching GitHub (and optional `--youtube` / `--channel` URLs):

```powershell
python -m src.generate wizard https://github.com/owner/your-repo `
  --youtube "https://www.youtube.com/watch?v=VIDEO_ID" -g
```

### Option C — Edit YAML manually

```powershell
python -m src.generate init my-project
# edit config/projects/my-project.yaml
python -m src.generate generate config/projects/my-project.yaml
```

### Refresh config from saved sources

If your YAML has a `sources:` block (auto-added), re-fetch GitHub/YouTube and regenerate:

```powershell
python -m src.generate generate config/projects/your-project.yaml --refresh
```

## Commands

| Command | Description |
|---------|-------------|
| `auto [url] [--repo] [--youtube] [-g]` | Auto-build YAML; GitHub only, YouTube only, or both |
| `wizard [url] [--repo] [--youtube] [-g]` | Interactive config + optional generate |
| `from-repo [url]` | Alias for `auto` |
| `generate <config.yaml> [--refresh]` | Generate SEO pack (optionally refresh YAML first) |
| `validate <config.yaml>` | Check config against GUIDE rules |
| `init <name>` | Copy example config for a new project |
| `list` | List configs in `config/projects/` |

## Config overview

Each project is a YAML file in `config/projects/`. Key sections:

- **`sources`** — input URLs and `mode`: `github`, `youtube`, or `both` (controls which output folders are generated)
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

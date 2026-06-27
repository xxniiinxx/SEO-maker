"""Derive rich social content from GitHub metadata when config fields are sparse."""

from __future__ import annotations

import re

DEVTO_MAX_TAGS = 4

TOPIC_NICHE_MAP = {
    "solana": "Solana Web3 development",
    "anchor": "Solana / Anchor smart contract development",
    "ethereum": "Ethereum dApp development",
    "polymarket": "Polymarket and prediction-market tooling",
    "defi": "DeFi and on-chain finance",
    "casino": "Web3 gaming and on-chain game development",
    "gambling": "Web3 gaming and on-chain game development",
    "betting": "Web3 gaming and peer-to-peer on-chain apps",
    "blockchain-game": "Blockchain game development",
    "coinflip": "Blockchain game development",
    "crypto-trading-bot": "Crypto trading bot development",
    "typescript-bot": "TypeScript automation and bot development",
}

TOPIC_SUBREDDIT_MAP = {
    "solana": "r/solana",
    "anchor": "r/solana",
    "ethereum": "r/ethdev",
    "defi": "r/defi",
    "blockchain-game": "r/Web3",
    "casino": "r/Web3",
    "gambling": "r/Web3",
    "typescript": "r/typescript",
    "javascript": "r/javascript",
    "programming": "r/programming",
    "opensource": "r/opensource",
}

TECH_KEYWORDS = [
    ("Solana", r"\bsolana\b"),
    ("Anchor", r"\banchor\b"),
    ("TypeScript", r"\btypescript\b|\.ts\b"),
    ("JavaScript", r"\bjavascript\b|node\.?js\b"),
    ("MongoDB", r"\bmongodb\b"),
    ("WebSockets", r"\bwebsockets?\b"),
    ("Orao VRF", r"\borao\b|\bvrf\b"),
    ("React", r"\breact\b"),
    ("Next.js", r"\bnext\.?js\b"),
    ("Solidity", r"\bsolidity\b"),
    ("Polymarket API", r"\bpolymarket\b"),
]


def _humanize_repo_name(repo_name: str) -> str:
    return repo_name.replace("-", " ").replace("_", " ").strip().title()


def extract_primary_keyword(
    description: str, repo_name: str, topics: list[str] | None = None
) -> str:
    """Avoid broken keywords like 'A full' from 'A full-stack...'."""
    desc = (description or "").strip()
    topics = topics or []

    match = re.search(
        r"((?:peer-to-peer\s+)?[\w\s,-]+?\s+on\s+(?:Solana|Ethereum|Bitcoin|Web3))",
        desc,
        re.I,
    )
    if match:
        phrase = match.group(1).strip()
        if len(phrase) >= 15:
            return phrase[0].upper() + phrase[1:] if phrase[0].islower() else phrase

    first_sentence = desc.split(".")[0].strip() if desc else ""
    first_sentence = re.sub(r"^(A|An|The)\s+", "", first_sentence, flags=re.I)
    if 18 <= len(first_sentence) <= 72:
        return first_sentence
    if len(first_sentence) > 72:
        trimmed = first_sentence[:69].rsplit(" ", 1)[0]
        if len(trimmed) >= 18:
            return trimmed

    human = _humanize_repo_name(repo_name)
    desc_lower = desc.lower()
    if "solana" in desc_lower and "solana" not in human.lower():
        return f"{human} on Solana"
    if topics:
        hint = TOPIC_NICHE_MAP.get(topics[0].lower(), "")
        if "Solana" in hint and "solana" not in human.lower():
            return f"{human} on Solana"
    return human


def infer_niche(description: str, topics: list[str], fallback: str = "") -> str:
    if fallback and fallback != "Open-source developer tools":
        return fallback
    for topic in topics:
        mapped = TOPIC_NICHE_MAP.get(topic.lower())
        if mapped:
            return mapped
    desc_lower = (description or "").lower()
    if "solana" in desc_lower:
        return "Solana Web3 development"
    if "polymarket" in desc_lower:
        return "Polymarket and prediction-market tooling"
    if "trading bot" in desc_lower:
        return "Crypto trading bot development"
    return fallback or "Open-source developer tools"


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


def parse_readme_features(readme: str) -> list[str]:
    """Extract bullet points from a README ## Features section."""
    if not readme:
        return []
    match = re.search(r"##\s*Features\s*\n(.*?)(?:\n##|\Z)", readme, re.I | re.S)
    if not match:
        return []
    features: list[str] = []
    for line in match.group(1).splitlines():
        bullet = re.match(r"^[\-*•]\s+(.+)", line.strip())
        if not bullet:
            continue
        item = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", bullet.group(1).strip())
        item = re.sub(r"`([^`]+)`", r"\1", item)
        if 8 < len(item) < 150 and item not in features:
            features.append(item)
    return features[:8]


def infer_repo_name_suggestions(
    repo_name: str, primary_keyword: str, topics: list[str]
) -> list[str]:
    suggestions = [repo_name]
    base = primary_keyword.lower()
    if "solana" in base and repo_name not in suggestions:
        suggestions.append(f"solana-{repo_name}" if "solana" not in repo_name else repo_name)
    for topic in topics[:3]:
        candidate = f"{topic}-{repo_name}" if topic not in repo_name else repo_name
        if candidate not in suggestions:
            suggestions.append(candidate)
    human = re.sub(r"[^a-z0-9]+", "-", primary_keyword.lower()).strip("-")[:40]
    if human and human not in suggestions and not human.startswith("a-full"):
        suggestions.append(human)
    return suggestions[:5]


def infer_features(
    description: str,
    topics: list[str],
    existing: list[str] | None = None,
    readme_excerpt: str = "",
) -> list[str]:
    features: list[str] = list(existing or [])
    desc = description or ""

    capability_patterns = [
        (r"wallet", "Wallet connect — players sign in with a Solana wallet"),
        (r"peer-to-peer|head-to-head", "Peer-to-peer rooms — create or join head-to-head matches"),
        (r"WebSocket", "Real-time UI synced over WebSockets"),
        (r"Orao|VRF|verifiable random", "Provably fair outcomes via on-chain VRF (Orao)"),
        (r"MongoDB", "Off-chain room state, chat, and match history in MongoDB"),
        (r"on-chain", "On-chain escrow and outcome resolution"),
        (r"2×|2x|double", "Winner takes 2× the stake on resolved flips"),
        (r"copy.?trad", "Automated copy-trading strategy execution"),
        (r"snipe|late-window", "Late-window snipe execution for short-interval markets"),
        (r"backtest|paper trad", "Backtesting and paper-trading modes"),
    ]
    desc_lower = desc.lower()
    for pattern, feature in capability_patterns:
        if re.search(pattern, desc_lower, re.I) and feature not in features:
            features.append(feature)

    for sentence in _sentences(desc):
        if sentence not in features and len(features) < 6:
            features.append(sentence.rstrip("."))

    if readme_excerpt:
        for line in readme_excerpt.splitlines():
            bullet = re.match(r"^[\-*•]\s+(.+)", line.strip())
            if bullet and len(features) < 8:
                item = bullet.group(1).strip()
                if re.match(r"^\[.+\]\(#.+\)$", item):
                    continue
                if item.startswith("[") and "](#" in item:
                    continue
                if 10 < len(item) < 120 and item not in features:
                    features.append(item)

    if not features and topics:
        features.append(f"Open-source {topics[0].replace('-', ' ')} tooling")
    return features[:8]


def infer_tech_stack(
    description: str,
    topics: list[str],
    language: str = "",
    existing: list[str] | None = None,
    readme_excerpt: str = "",
) -> list[str]:
    if existing and len(existing) > 1:
        return existing

    stack: list[str] = []
    haystack = " ".join([description, readme_excerpt, " ".join(topics)]).lower()

    for label, pattern in TECH_KEYWORDS:
        if re.search(pattern, haystack, re.I) and label not in stack:
            stack.append(label)

    if language and language not in stack:
        stack.insert(0, language)

    if "JavaScript" in stack and "TypeScript" in stack:
        stack = [s for s in stack if s != "JavaScript"]

    topic_labels = {
        "anchor": "Anchor",
        "mongodb": "MongoDB",
        "typescript": "TypeScript",
    }
    for topic in topics:
        label = topic_labels.get(topic.lower())
        if label and label not in stack:
            stack.append(label)

    if not stack and language:
        return [language]
    return stack[:10]


def infer_use_cases(
    description: str,
    topics: list[str],
    repo_name: str,
    niche: str,
    existing: list[str] | None = None,
) -> list[str]:
    if existing:
        return existing

    cases: list[str] = []
    desc_lower = (description or "").lower()
    human = _humanize_repo_name(repo_name)

    if "game" in desc_lower or "casino" in desc_lower or "coinflip" in desc_lower:
        cases.extend(
            [
                "Learn full-stack Web3 game architecture (wallet + program + backend + UI)",
                "Study provably fair randomness with on-chain VRF integration",
                "Fork and customize a peer-to-peer on-chain betting room model",
            ]
        )
    elif "bot" in desc_lower or "trading" in desc_lower:
        cases.extend(
            [
                "Automate trading or snipe strategies with a typed codebase",
                "Backtest ideas before deploying with real capital",
                "Extend the bot with your own risk rules and market filters",
            ]
        )
    else:
        cases.extend(
            [
                f"Explore {_humanize_repo_name(repo_name).lower()} patterns in {niche.lower()}",
                "Fork the repo as a starter template for your own project",
                "Contribute features, docs, or tests via pull requests",
            ]
        )

    return cases[:4]


def pick_devto_tags(topics: list[str], language: str = "", description: str = "") -> list[str]:
    preferred = []
    priority = [
        "solana",
        "web3",
        "blockchain",
        "typescript",
        "javascript",
        "anchor",
        "programming",
        "opensource",
        "tutorial",
        "defi",
    ]
    topic_set = {t.lower() for t in topics}
    desc_lower = (description or "").lower()
    if "solana" in desc_lower:
        topic_set.add("solana")
    if "web3" in desc_lower or "on-chain" in desc_lower:
        topic_set.add("web3")

    for tag in priority:
        if tag in topic_set or (tag == "typescript" and language.lower() == "typescript"):
            preferred.append(tag)
    for topic in topics:
        if topic.lower() not in preferred and topic.lower() not in {"gambling", "betting", "casino"}:
            preferred.append(topic.lower())
    if language and language.lower() not in preferred:
        preferred.append(language.lower())
    return preferred[:DEVTO_MAX_TAGS]


def pick_hashtags(topics: list[str], primary_keyword: str) -> list[str]:
    tags: list[str] = []
    for topic in topics[:6]:
        clean = re.sub(r"[^a-zA-Z0-9]", "", topic)
        if clean and clean.lower() not in {t.lower() for t in tags}:
            tags.append(clean)
    for word in ["opensource", "web3", "buildinpublic"]:
        if word not in {t.lower() for t in tags}:
            tags.append(word)
    return tags[:6]


def pick_subreddits(topics: list[str], niche: str) -> list[str]:
    subs: list[str] = []
    for topic in topics:
        sub = TOPIC_SUBREDDIT_MAP.get(topic.lower())
        if sub and sub not in subs:
            subs.append(sub)
    if not subs:
        subs = ["r/opensource", "r/programming", "r/Web3"]
    if "r/opensource" not in subs:
        subs.append("r/opensource")
    return subs[:6]


def devto_title(primary_keyword: str, description: str, max_len: int = 128, *, video: bool = False) -> str:
    if video:
        title = f"New tutorial: {primary_keyword}"
    else:
        title = f"I open-sourced {primary_keyword}"
    if len(title) <= max_len:
        return title
    return primary_keyword[: max_len - 3] + "..."


def video_setup_steps(video_url: str = "") -> list[str]:
    steps = [
        "Watch the full video on YouTube",
        "Follow along with the steps shown on screen",
        "Subscribe for more tutorials in this series",
    ]
    if video_url:
        steps.insert(0, f"Open the video: {video_url}")
    return steps


def setup_steps(repo_name: str) -> list[str]:
    return [
        "Install dependencies (see README — typically npm install or yarn)",
        "Copy .env.example to .env and fill in RPC, wallet, and API keys",
        "Run local validator or point to devnet/mainnet as documented",
        "Start the backend and frontend; connect wallet and create a test room",
    ]


def architecture_points(description: str, features: list[str], tech_stack: list[str]) -> list[str]:
    points: list[str] = []
    desc = (description or "").lower()

    if "wallet" in desc or "on-chain" in desc:
        points.append("**Wallet layer** — users connect a Web3 wallet to sign transactions")
    if "anchor" in desc or any("anchor" in t.lower() for t in tech_stack):
        points.append("**On-chain program** — Anchor/Rust logic for escrow, rooms, and settlement")
    if "vrf" in desc or "orao" in desc:
        points.append("**Randomness** — verifiable flip outcomes via Orao VRF on Solana")
    if "websocket" in desc:
        points.append("**Real-time layer** — WebSocket events push room and flip state to the UI")
    if "mongodb" in desc or any("mongo" in t.lower() for t in tech_stack):
        points.append("**Persistence** — MongoDB stores rooms, chat, and historical match data")
    if "typescript" in desc or any("typescript" in t.lower() for t in tech_stack):
        points.append("**Application layer** — TypeScript backend/frontend tying on-chain and off-chain flows")

    if len(points) < 3 and features:
        for feature in features[:3]:
            points.append(f"**Feature** — {feature}")

    return points[:6]


def enrich_social_context(config: dict, readme_excerpt: str = "") -> dict:
    """Return template context with inferred fields filled in."""
    github = dict(config.get("github") or {})
    social = dict(config.get("social") or {})
    description = github.get("short_description") or ""
    topics = github.get("topics") or []
    repo_name = github.get("repo_name") or config.get("project_name") or "project"
    language = github.get("language") or ""

    readme = readme_excerpt or github.get("readme_excerpt") or ""

    primary = github.get("primary_keyword") or ""
    broken = {"a full", "open source", "open-source", "the", "a", "an"}
    if not primary or len(primary) < 10 or primary.lower() in broken:
        primary = extract_primary_keyword(description, repo_name, topics)
    github["primary_keyword"] = primary

    niche = infer_niche(description, topics, config.get("niche") or "")
    github["features"] = infer_features(description, topics, github.get("features"), readme)
    github["tech_stack"] = infer_tech_stack(
        description, topics, language, github.get("tech_stack"), readme
    )
    github["use_cases"] = infer_use_cases(
        description, topics, repo_name, niche, github.get("use_cases")
    )

    devto_tags = pick_devto_tags(topics, language, description)
    if not social.get("hashtags"):
        social["hashtags"] = pick_hashtags(topics, primary)
    if not social.get("subreddits"):
        social["subreddits"] = pick_subreddits(topics, niche)

    sources = config.get("sources") or {}
    youtube = config.get("youtube") or {}
    video_url = ""
    if youtube.get("videos"):
        video_url = youtube["videos"][0].get("youtube_url") or ""
    if not video_url and (config.get("cross_links") or {}).get("youtube_videos"):
        video_url = config["cross_links"]["youtube_videos"][0].get("url") or ""

    is_video_only = sources.get("mode") == "youtube" or (
        not github.get("repo_url") and bool(youtube.get("videos"))
    )

    if is_video_only:
        steps = video_setup_steps(video_url)
        cover = "Add a cover image: use your YouTube thumbnail or a custom 1000×420 banner"
        title = devto_title(primary, description, video=True)
    else:
        steps = setup_steps(repo_name)
        cover = (
            f"Add a cover image: screenshot of {repo_name} UI or architecture diagram "
            f"(recommended 1000×420 for dev.to)"
        )
        title = devto_title(primary, description)

    enriched = {
        "devto_tags": devto_tags,
        "devto_title": title,
        "setup_steps": steps,
        "architecture_points": architecture_points(
            description, github["features"], github["tech_stack"]
        ),
        "cover_image_hint": cover,
        "is_video_only": is_video_only,
        "primary_video_url": video_url,
    }

    return {
        **config,
        "github": github,
        "social": social,
        "niche": niche,
        **enriched,
    }

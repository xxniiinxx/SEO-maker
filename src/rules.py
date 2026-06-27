"""SEO validation rules derived from GUIDEs."""

GITHUB_ABOUT_MAX = 350
GITHUB_TOPICS_MIN = 5
GITHUB_TOPICS_MAX = 10
YOUTUBE_TITLE_MAX = 70
YOUTUBE_DESCRIPTION_LEAD_MAX = 150
YOUTUBE_TAGS_MIN = 10
YOUTUBE_TAGS_MAX = 15


def _warn(message: str) -> str:
    return f"WARNING: {message}"


def validate_github(github: dict) -> list[str]:
    warnings: list[str] = []
    about = github.get("short_description", "")
    if len(about) > GITHUB_ABOUT_MAX:
        warnings.append(
            _warn(
                f"About/description is {len(about)} chars (GitHub limit ~{GITHUB_ABOUT_MAX})."
            )
        )

    topics = github.get("topics") or []
    if len(topics) < GITHUB_TOPICS_MIN:
        warnings.append(
            _warn(
                f"Only {len(topics)} topics — aim for {GITHUB_TOPICS_MIN}–{GITHUB_TOPICS_MAX}."
            )
        )
    elif len(topics) > GITHUB_TOPICS_MAX:
        warnings.append(
            _warn(
                f"{len(topics)} topics — GitHub allows up to 20; {GITHUB_TOPICS_MAX} is recommended."
            )
        )

    if not github.get("primary_keyword"):
        warnings.append(_warn("Missing primary_keyword for GitHub."))

    keyword = (github.get("primary_keyword") or "").lower()
    if keyword and keyword not in about.lower():
        warnings.append(
            _warn("Primary keyword should appear in the About/short description.")
        )

    return warnings


def validate_youtube_video(
    video: dict, video_id: str = "unknown", config: dict | None = None
) -> list[str]:
    warnings: list[str] = []
    title = build_youtube_title(video)
    if len(title) > YOUTUBE_TITLE_MAX:
        warnings.append(
            _warn(
                f"[{video_id}] Title is {len(title)} chars (max {YOUTUBE_TITLE_MAX}): {title!r}"
            )
        )

    for variant in build_youtube_title_variants(video):
        if len(variant) > YOUTUBE_TITLE_MAX:
            warnings.append(
                _warn(
                    f"[{video_id}] Title variant exceeds {YOUTUBE_TITLE_MAX} chars "
                    f"({len(variant)}): {variant!r}"
                )
            )

    lead = build_description_lead(video)
    if len(lead) > YOUTUBE_DESCRIPTION_LEAD_MAX:
        warnings.append(
            _warn(
                f"[{video_id}] Description lead is {len(lead)} chars "
                f"(target ≤{YOUTUBE_DESCRIPTION_LEAD_MAX})."
            )
        )

    if not video.get("timestamps"):
        warnings.append(
            _warn(f"[{video_id}] No timestamps — add chapters for SEO and UX.")
        )

    tags = build_youtube_tags(video, config or {})
    if len(tags) < YOUTUBE_TAGS_MIN:
        warnings.append(
            _warn(
                f"[{video_id}] Suggest {YOUTUBE_TAGS_MIN}–{YOUTUBE_TAGS_MAX} tags; "
                f"generating {len(tags)}."
            )
        )

    return warnings


def build_youtube_title(video: dict) -> str:
    keyword = video.get("primary_keyword", "")
    year = video.get("year", "")
    topic = video.get("video_topic", "")
    title = f"{keyword} {year}".strip()
    if topic and topic.lower() not in title.lower():
        title = f"{keyword} {year}: {topic}".strip(": ").strip()
    if len(title) > YOUTUBE_TITLE_MAX:
        title = f"{keyword} {year}".strip()
    return title.strip()


def build_youtube_title_variants(video: dict) -> list[str]:
    keyword = video.get("primary_keyword", "")
    year = str(video.get("year", ""))
    topic = video.get("video_topic", "")
    variants: list[str] = []

    candidates = [
        build_youtube_title(video),
        f"{keyword} Tutorial {year}".strip(),
        f"How to {topic}".strip() if topic else "",
        f"{keyword} — {topic} ({year})".strip() if topic else "",
        f"{topic} | {keyword}".strip() if topic else "",
    ]
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            variants.append(candidate)
    return variants


def build_description_lead(video: dict) -> str:
    keyword = video.get("primary_keyword", "")
    topic = video.get("video_topic", "")
    lead = f"{keyword} — {topic}. Step-by-step guide." if topic else f"{keyword}. Step-by-step guide."
    if len(lead) > YOUTUBE_DESCRIPTION_LEAD_MAX:
        lead = f"{keyword} — {topic[:80]}".strip(" —")
    return lead


def build_youtube_tags(video: dict, config: dict) -> list[str]:
    tags: list[str] = []
    if video.get("primary_keyword"):
        tags.append(video["primary_keyword"])
    tags.extend(video.get("secondary_keywords") or [])
    github = config.get("github") or {}
    for item in github.get("topics") or []:
        tags.append(item.replace("-", " "))
    extras = ["crypto", "trading bot", "tutorial", "open source", "developer tools"]
    tags.extend(extras)
    if github.get("repo_name"):
        tags.append(github["repo_name"].replace("-", " "))
    for playlist in (config.get("youtube") or {}).get("playlists") or []:
        tags.append(playlist)

    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        normalized = tag.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
        if len(result) >= YOUTUBE_TAGS_MAX:
            break
    return result


DEVTO_MAX_TAGS = 4
DEVTO_MIN_WORDS_HINT = 400


def validate_social(config: dict) -> list[str]:
    warnings: list[str] = []
    github = config.get("github") or {}
    primary = github.get("primary_keyword") or ""

    if len(primary) < 10:
        warnings.append(_warn("social: primary_keyword looks too short for post titles."))

    devto_tags = config.get("devto_tags") or []
    if len(devto_tags) > DEVTO_MAX_TAGS:
        warnings.append(_warn(f"social/devto: use at most {DEVTO_MAX_TAGS} tags on dev.to."))

    features = github.get("features") or []
    if len(features) < 3:
        warnings.append(_warn("social: fewer than 3 features — posts may feel thin."))

    if not config.get("architecture_points"):
        warnings.append(_warn("social: no architecture points generated — review dev.to post."))

    return warnings

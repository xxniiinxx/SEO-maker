from pathlib import Path

from src.render import render
from src.rules import (
    build_description_lead,
    build_youtube_tags,
    build_youtube_title_variants,
    validate_youtube_video,
)


def generate_youtube_pack(config: dict, output_dir: Path) -> list[str]:
    youtube = config.get("youtube") or {}
    warnings: list[str] = []
    out = output_dir / "youtube"
    out.mkdir(parents=True, exist_ok=True)

    ctx = {
        "config": config,
        "github": config.get("github") or {},
        "cross_links": config.get("cross_links") or {},
        "youtube": youtube,
        "social": config.get("social") or {},
        "niche": config.get("niche", ""),
        "project_name": config.get("project_name", ""),
    }

    (out / "channel-about.txt").write_text(
        render("youtube/channel-about.txt.j2", **ctx), encoding="utf-8"
    )
    (out / "playlists.txt").write_text(
        render("youtube/playlists.txt.j2", **ctx), encoding="utf-8"
    )

    for video in youtube.get("videos") or []:
        video_id = video.get("id", "video")
        video_dir = out / video_id
        video_dir.mkdir(parents=True, exist_ok=True)

        video_ctx = {
            **ctx,
            "video": video,
            "title_variants": build_youtube_title_variants(video),
            "description_lead": build_description_lead(video),
            "tags": build_youtube_tags(video, config),
        }

        (video_dir / "title-variants.txt").write_text(
            render("youtube/title-variants.txt.j2", **video_ctx), encoding="utf-8"
        )
        (video_dir / "description.txt").write_text(
            render("youtube/description.txt.j2", **video_ctx), encoding="utf-8"
        )
        (video_dir / "tags.txt").write_text(
            render("youtube/tags.txt.j2", **video_ctx), encoding="utf-8"
        )
        (video_dir / "end-screen-cards.txt").write_text(
            render("youtube/end-screen-cards.txt.j2", **video_ctx), encoding="utf-8"
        )

        warnings.extend(validate_youtube_video(video, video_id, config))

    if warnings:
        (out / "warnings.txt").write_text("\n".join(warnings) + "\n", encoding="utf-8")

    return warnings

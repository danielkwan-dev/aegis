"""Parses an official Instagram "Download Your Data" export (.zip) into
raw post records (caption, timestamp, image bytes) ready for ingestion.

Two real-world gotchas handled here:
  - Instagram's JSON export mojibake bug: text fields are UTF-8 bytes that
    got JSON-escaped as if they were Latin-1, so "café" comes out as
    "cafÃ©" unless re-decoded.
  - The export's internal file layout has shifted across versions (posts
    JSON has lived at different paths, media references have used
    different relative-path conventions), so this searches the archive
    for posts_*.json rather than assuming one fixed path.
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

POSTS_JSON_PATTERN = re.compile(r"posts_\d+\.json$")


class InstagramExportError(ValueError):
    """Raised when the uploaded file isn't a recognizable Instagram export."""


def _fix_instagram_mojibake(value: str) -> str:
    try:
        return value.encode("latin1").decode("utf8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _find_posts_json_members(zf: zipfile.ZipFile) -> list[str]:
    return sorted(n for n in zf.namelist() if POSTS_JSON_PATTERN.search(n))


def _extract_caption(post: dict) -> str:
    if post.get("title"):
        return _fix_instagram_mojibake(post["title"])
    for media in post.get("media", []):
        if media.get("title"):
            return _fix_instagram_mojibake(media["title"])
    return ""


def _extract_timestamp(post: dict) -> datetime | None:
    ts = post.get("creation_timestamp")
    if ts is None:
        for media in post.get("media", []):
            if media.get("creation_timestamp") is not None:
                ts = media["creation_timestamp"]
                break
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _first_media_uri(post: dict) -> str | None:
    media_list = post.get("media", [])
    if media_list:
        return media_list[0].get("uri")
    return None


def _read_media_bytes(zf: zipfile.ZipFile, media_uri: str) -> bytes | None:
    namelist = zf.namelist()
    if media_uri in namelist:
        with zf.open(media_uri) as f:
            return f.read()

    # Export layouts have moved media around across versions — fall back to
    # matching just the filename anywhere in the archive.
    basename = Path(media_uri).name
    for name in namelist:
        if name.endswith("/" + basename) or name == basename:
            with zf.open(name) as f:
                return f.read()
    return None


def parse_instagram_export(file_obj: BinaryIO) -> list[dict]:
    """Parse an Instagram data-export zip into [{caption, timestamp, image_bytes}, ...].

    `file_obj` should be a seekable binary stream. FastAPI's UploadFile
    already spools large uploads to a temp file on disk rather than memory,
    so this never materializes the whole archive at once — only the (small)
    posts_*.json metadata is read in full; each post's photo is opened
    lazily, one at a time.
    """
    posts: list[dict] = []

    try:
        zf = zipfile.ZipFile(file_obj)
    except zipfile.BadZipFile as e:
        raise InstagramExportError("That file isn't a valid .zip archive.") from e

    with zf:
        posts_members = _find_posts_json_members(zf)
        if not posts_members:
            raise InstagramExportError(
                "No posts_*.json found in this archive. Make sure you uploaded "
                "the full Instagram data export .zip, not a partial extract."
            )

        raw_posts: list[dict] = []
        for member in posts_members:
            with zf.open(member) as f:
                data = json.load(f)
            raw_posts.extend(data if isinstance(data, list) else data.get("posts", []))

        for raw in raw_posts:
            caption = _extract_caption(raw)
            timestamp = _extract_timestamp(raw)
            media_uri = _first_media_uri(raw)

            image_bytes = _read_media_bytes(zf, media_uri) if media_uri else None

            if not caption and not image_bytes:
                continue

            posts.append({
                "caption": caption,
                "timestamp": timestamp,
                "image_bytes": image_bytes,
            })

    return posts

import io
import json
import zipfile
from datetime import datetime, timezone

import pytest

from app.services.ingestion import InstagramExportError, parse_instagram_export


def _build_export_zip(posts: list[dict], *, posts_path: str = "your_instagram_activity/content/posts_1.json") -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(posts_path, json.dumps(posts))
        for post in posts:
            for media in post.get("media", []):
                zf.writestr(media["uri"], b"\xff\xd8\xff\xe0fake-jpeg-bytes")
    buf.seek(0)
    return buf


def test_parses_caption_timestamp_and_image():
    ts = int(datetime(2026, 1, 15, 7, 30, tzinfo=timezone.utc).timestamp())
    zf = _build_export_zip([
        {
            "media": [{"uri": "media/posts/202601/photo1.jpg", "creation_timestamp": ts, "title": "Morning coffee on Market Street"}],
        }
    ])

    posts = parse_instagram_export(zf)

    assert len(posts) == 1
    assert posts[0]["caption"] == "Morning coffee on Market Street"
    assert posts[0]["timestamp"] == datetime.fromtimestamp(ts, tz=timezone.utc)
    assert posts[0]["image_bytes"] == b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def test_fixes_instagram_mojibake():
    # Instagram JSON-escapes UTF-8 bytes as if they were Latin-1 —
    # "café" ends up encoded as the mojibake string below in real exports.
    mojibake_caption = "cafÃ©"
    zf = _build_export_zip([
        {"media": [{"uri": "media/posts/202601/photo1.jpg", "creation_timestamp": 1700000000, "title": mojibake_caption}]}
    ])

    posts = parse_instagram_export(zf)

    assert posts[0]["caption"] == "café"


def test_falls_back_to_basename_when_media_path_moved():
    # Simulate an export-version mismatch: the JSON references a path that
    # doesn't exist verbatim in the archive, only its basename does.
    zf_buf = io.BytesIO()
    posts = [{"media": [{"uri": "media/posts/202601/photo1.jpg", "creation_timestamp": 1700000000, "title": "test"}]}]
    with zipfile.ZipFile(zf_buf, "w") as zf:
        zf.writestr("your_instagram_activity/content/posts_1.json", json.dumps(posts))
        # Actual file lives under a different directory than the JSON claims.
        zf.writestr("media/other_location/photo1.jpg", b"image-bytes")
    zf_buf.seek(0)

    parsed = parse_instagram_export(zf_buf)

    assert parsed[0]["image_bytes"] == b"image-bytes"


def test_skips_posts_with_no_caption_and_no_image():
    zf = _build_export_zip([{"media": []}])

    posts = parse_instagram_export(zf)

    assert posts == []


def test_raises_on_missing_posts_json():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("some_other_file.json", "{}")
    buf.seek(0)

    with pytest.raises(InstagramExportError):
        parse_instagram_export(buf)


def test_raises_on_non_zip_file():
    with pytest.raises(InstagramExportError):
        parse_instagram_export(io.BytesIO(b"not a zip file"))

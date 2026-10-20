from pathlib import Path

from md2wp.media import (
    collect_local_images,
    resolve_featured_path,
    rewrite_image_srcs,
)

FIXTURES = Path(__file__).parent / "fixtures" / "media-post"


def test_collect_local_images_skips_remote_and_missing(tmp_path):
    (tmp_path / "ok.png").write_bytes(b"x")
    html = (
        '<p><img src="ok.png"/>'
        '<img src="https://cdn.example.com/a.png"/>'
        '<img src="data:image/png;base64,abc"/>'
        '<img src="missing.png"/></p>'
    )
    found = collect_local_images(html, tmp_path)
    assert len(found) == 1
    assert found[0][0] == "ok.png"
    assert found[0][1] == (tmp_path / "ok.png").resolve()


def test_rewrite_image_srcs():
    html = '<p><img src="a.png"/><img src="https://x/y.png"/></p>'
    out = rewrite_image_srcs(html, {"a.png": "https://wp.example/media/a.png"})
    assert "https://wp.example/media/a.png" in out
    assert "https://x/y.png" in out


def test_resolve_featured_path():
    cover = FIXTURES / "images" / "cover.png"
    assert resolve_featured_path("images/cover.png", FIXTURES) == cover.resolve()
    assert resolve_featured_path("images/nope.png", FIXTURES) is None
    assert resolve_featured_path("https://cdn.example.com/x.png", FIXTURES) is None

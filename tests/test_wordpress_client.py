from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from md2wp.config import PostStatus, Settings
from md2wp.models import Post, PostMetadata
from md2wp.sinks.wordpress import WordPressClient, publish_to_wordpress

FIXTURES = Path(__file__).parent / "fixtures" / "media-post"


def _sample_post(slug: str = "my-post") -> Post:
    return Post(
        metadata=PostMetadata(
            title="Test Post",
            date=datetime(2024, 8, 13, 16, 42, 19),
            slug=slug,
            tags=["Go"],
            categories=["TechBlog"],
            lang="en",
            shortlink="https://example.com/s/abc",
        ),
        html_content="<p>Hello</p>",
    )


def _media_post() -> Post:
    return Post(
        metadata=PostMetadata(
            title="Post With Images",
            date=datetime(2024, 8, 13, 16, 42, 19),
            slug="post-with-images",
            featured_image="images/cover.png",
            source_path=FIXTURES / "post.md",
            tags=[],
            categories=[],
        ),
        html_content=(
            '<p><img alt="Inline" src="images/inline.png"/>'
            '<img alt="Remote" src="https://cdn.example.com/remote.png"/></p>'
        ),
    )


def test_publish_creates_post(mocker):
    settings = Settings(
        wordpress_url="https://example.com/wp-json/wp/v2",
        wordpress_username="admin",
        wordpress_password="secret",
        status=PostStatus.DRAFT,
    )
    client = WordPressClient(settings)

    responses = {
        ("GET", "/users/me"): MagicMock(status_code=200, json=lambda: {"id": 1}),
        ("GET", "/tags"): MagicMock(status_code=200, json=lambda: []),
        ("POST", "/tags"): MagicMock(status_code=201, json=lambda: {"id": 10}),
        ("GET", "/categories"): MagicMock(status_code=200, json=lambda: []),
        ("POST", "/categories"): MagicMock(status_code=201, json=lambda: {"id": 20}),
        ("GET", "/posts"): MagicMock(status_code=200, json=lambda: []),
        ("POST", "/posts"): MagicMock(status_code=201, json=lambda: {"id": 100}),
        ("POST", "/posts/100/meta"): MagicMock(status_code=201, json=lambda: {}),
    }

    def fake_request(method, path, **kwargs):
        key = (method, path.split("?")[0])
        return responses[key]

    mocker.patch.object(client, "_request", side_effect=fake_request)

    action, post_id = client.publish_post(_sample_post())
    assert action == "created"
    assert post_id == 100


def test_publish_updates_existing_post(mocker):
    settings = Settings(
        wordpress_url="https://example.com/wp-json/wp/v2",
        wordpress_username="admin",
        wordpress_password="secret",
    )
    client = WordPressClient(settings)

    responses = {
        ("GET", "/users/me"): MagicMock(status_code=200, json=lambda: {"id": 1}),
        ("GET", "/tags"): MagicMock(status_code=200, json=lambda: [{"id": 10, "name": "Go"}]),
        ("GET", "/categories"): MagicMock(
            status_code=200, json=lambda: [{"id": 20, "name": "TechBlog"}]
        ),
        ("GET", "/posts"): MagicMock(status_code=200, json=lambda: [{"id": 55, "slug": "my-post"}]),
        ("PUT", "/posts/55"): MagicMock(status_code=200, json=lambda: {"id": 55}),
        ("POST", "/posts/55/meta"): MagicMock(status_code=201, json=lambda: {}),
    }

    def fake_request(method, path, **kwargs):
        key = (method, path.split("?")[0])
        return responses[key]

    mocker.patch.object(client, "_request", side_effect=fake_request)

    action, post_id = client.publish_post(_sample_post())
    assert action == "updated"
    assert post_id == 55


def test_publish_uploads_media_rewrites_and_sets_featured(mocker):
    settings = Settings(
        wordpress_url="https://example.com/wp-json/wp/v2",
        wordpress_username="admin",
        wordpress_password="secret",
        status=PostStatus.DRAFT,
    )
    client = WordPressClient(settings)
    captured: dict = {}

    next_media_id = {"n": 500}

    def fake_request(method, path, **kwargs):
        key = path.split("?")[0]
        if method == "GET" and key == "/media":
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key == "/media":
            mid = next_media_id["n"]
            next_media_id["n"] += 1
            filename = "cover.png" if mid == 500 else "inline.png"
            # First upload is inline (content order), then cover if separate —
            # order depends on collect then featured. Content first: inline, then cover.
            files = kwargs.get("files") or {}
            file_tuple = files.get("file")
            if file_tuple:
                filename = file_tuple[0]
            url = f"https://example.com/wp-content/uploads/{filename}"
            return MagicMock(
                status_code=201,
                json=lambda mid=mid, url=url: {"id": mid, "source_url": url},
            )
        if method == "GET" and key == "/posts":
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key == "/posts":
            captured["payload"] = kwargs.get("json")
            return MagicMock(status_code=201, json=lambda: {"id": 100})
        return MagicMock(status_code=200, json=lambda: {})

    mocker.patch.object(client, "_request", side_effect=fake_request)

    action, post_id = client.publish_post(_media_post())
    assert action == "created"
    assert post_id == 100

    payload = captured["payload"]
    assert "images/inline.png" not in payload["content"]
    assert "https://example.com/wp-content/uploads/inline.png" in payload["content"]
    assert "https://cdn.example.com/remote.png" in payload["content"]
    assert "featured_media" in payload
    assert isinstance(payload["featured_media"], int)


def test_publish_reuses_existing_media(mocker):
    settings = Settings(
        wordpress_url="https://example.com/wp-json/wp/v2",
        wordpress_username="admin",
        wordpress_password="secret",
    )
    client = WordPressClient(settings)
    uploads = {"count": 0}
    captured: dict = {}

    def fake_request(method, path, **kwargs):
        key = path.split("?")[0]
        if method == "GET" and key == "/media":
            search = (kwargs.get("params") or {}).get("search", "")
            if search == "inline.png":
                return MagicMock(
                    status_code=200,
                    json=lambda: [
                        {
                            "id": 11,
                            "slug": "inline",
                            "source_url": "https://example.com/wp-content/uploads/inline.png",
                        }
                    ],
                )
            if search == "cover.png":
                return MagicMock(
                    status_code=200,
                    json=lambda: [
                        {
                            "id": 12,
                            "slug": "cover",
                            "source_url": "https://example.com/wp-content/uploads/cover.png",
                        }
                    ],
                )
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key == "/media":
            uploads["count"] += 1
            return MagicMock(status_code=201, json=lambda: {"id": 99, "source_url": "x"})
        if method == "GET" and key == "/posts":
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key == "/posts":
            captured["payload"] = kwargs.get("json")
            return MagicMock(status_code=201, json=lambda: {"id": 100})
        return MagicMock(status_code=200, json=lambda: {})

    mocker.patch.object(client, "_request", side_effect=fake_request)

    client.publish_post(_media_post())
    assert uploads["count"] == 0
    assert captured["payload"]["featured_media"] == 12
    assert "https://example.com/wp-content/uploads/inline.png" in captured["payload"]["content"]


def test_publish_to_wordpress_counts_failures(mocker):
    settings = Settings(
        wordpress_url="https://example.com/wp-json/wp/v2",
        wordpress_username="admin",
        wordpress_password="secret",
    )
    client = WordPressClient(settings)
    mocker.patch.object(client, "_ensure_auth")
    mocker.patch.object(
        client,
        "publish_post",
        side_effect=[("created", 1), RuntimeError("boom")],
    )
    mocker.patch("md2wp.sinks.wordpress.WordPressClient", return_value=client)

    result = publish_to_wordpress([_sample_post("a"), _sample_post("b")], settings)
    assert result.published == 1
    assert result.failed == 1

from datetime import datetime
from unittest.mock import MagicMock

from md2wp.config import PostStatus, Settings
from md2wp.models import Post, PostMetadata
from md2wp.sinks.wordpress import WordPressClient, publish_to_wordpress


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

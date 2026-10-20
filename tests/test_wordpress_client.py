from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from md2wp.config import I18nProvider, PostStatus, Settings, WordPressI18nSettings
from md2wp.models import Post, PostMetadata
from md2wp.sinks.wordpress import WordPressClient, publish_to_wordpress

FIXTURES = Path(__file__).parent / "fixtures" / "media-post"


def _sample_post(slug: str = "my-post", lang: str = "en") -> Post:
    return Post(
        metadata=PostMetadata(
            title="Test Post",
            date=datetime(2024, 8, 13, 16, 42, 19),
            slug=slug,
            tags=["Go"],
            categories=["TechBlog"],
            lang=lang,
            shortlink="https://example.com/s/abc",
        ),
        html_content="<p>Hello</p>",
    )


def _wp_settings(*, provider: I18nProvider = I18nProvider.NONE) -> Settings:
    return Settings(
        wordpress_url="https://example.com/wp-json/wp/v2",
        wordpress_username="admin",
        wordpress_password="secret",
        status=PostStatus.DRAFT,
        wordpress_i18n=WordPressI18nSettings(provider=provider),
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


def test_polylang_passes_lang_query_params_on_create(mocker):
    client = WordPressClient(_wp_settings(provider=I18nProvider.POLYLANG))
    captured: list[tuple[str, str, dict]] = []
    meta_calls: list[tuple[str, str]] = []

    def fake_request(method, path, **kwargs):
        key = path.split("?")[0]
        captured.append((method, key, dict(kwargs.get("params") or {})))
        if method == "GET" and key == "/posts":
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key == "/posts":
            return MagicMock(status_code=201, json=lambda: {"id": 100, "lang": "fr"})
        if method == "POST" and key == "/posts/100/meta":
            body = kwargs.get("json") or {}
            meta_calls.append((body.get("key"), body.get("value")))
            return MagicMock(status_code=201, json=lambda: {})
        if method == "GET" and key in ("/tags", "/categories"):
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key in ("/tags", "/categories"):
            return MagicMock(status_code=201, json=lambda: {"id": 1})
        return MagicMock(status_code=200, json=lambda: {})

    mocker.patch.object(client, "_request", side_effect=fake_request)

    action, post_id = client.publish_post(_sample_post(lang="fr"))
    assert action == "created"
    assert post_id == 100

    get_posts = next(c for c in captured if c[0] == "GET" and c[1] == "/posts")
    assert get_posts[2].get("lang") == "fr"
    assert get_posts[2].get("slug") == "my-post"

    post_create = next(c for c in captured if c[0] == "POST" and c[1] == "/posts")
    assert post_create[2] == {"lang": "fr"}
    assert ("lang", "fr") in meta_calls


def test_polylang_passes_lang_query_params_on_update(mocker):
    client = WordPressClient(_wp_settings(provider=I18nProvider.POLYLANG))
    captured: list[tuple[str, str, dict]] = []

    def fake_request(method, path, **kwargs):
        key = path.split("?")[0]
        captured.append((method, key, dict(kwargs.get("params") or {})))
        if method == "GET" and key == "/posts":
            return MagicMock(
                status_code=200, json=lambda: [{"id": 55, "slug": "my-post", "lang": "fr"}]
            )
        if method == "PUT" and key == "/posts/55":
            return MagicMock(status_code=200, json=lambda: {"id": 55, "lang": "fr"})
        if method == "GET" and key in ("/tags", "/categories"):
            return MagicMock(
                status_code=200,
                json=lambda: (
                    [{"id": 10, "name": "Go"}]
                    if key == "/tags"
                    else [{"id": 20, "name": "TechBlog"}]
                ),
            )
        return MagicMock(status_code=200, json=lambda: {})

    mocker.patch.object(client, "_request", side_effect=fake_request)

    action, post_id = client.publish_post(_sample_post(lang="fr"))
    assert action == "updated"
    assert post_id == 55

    put = next(c for c in captured if c[0] == "PUT" and c[1] == "/posts/55")
    assert put[2] == {"lang": "fr"}


def test_wpml_passes_wpml_language_query_params(mocker):
    client = WordPressClient(_wp_settings(provider=I18nProvider.WPML))
    captured: list[tuple[str, str, dict]] = []
    meta_calls: list[tuple[str, str]] = []

    def fake_request(method, path, **kwargs):
        key = path.split("?")[0]
        captured.append((method, key, dict(kwargs.get("params") or {})))
        if method == "GET" and key == "/posts":
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key == "/posts":
            return MagicMock(
                status_code=201, json=lambda: {"id": 100, "wpml_language": "fr"}
            )
        if method == "POST" and key == "/posts/100/meta":
            body = kwargs.get("json") or {}
            meta_calls.append((body.get("key"), body.get("value")))
            return MagicMock(status_code=201, json=lambda: {})
        if method == "GET" and key in ("/tags", "/categories"):
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key in ("/tags", "/categories"):
            return MagicMock(status_code=201, json=lambda: {"id": 1})
        return MagicMock(status_code=200, json=lambda: {})

    mocker.patch.object(client, "_request", side_effect=fake_request)

    action, post_id = client.publish_post(_sample_post(lang="fr"))
    assert action == "created"
    assert post_id == 100

    get_posts = next(c for c in captured if c[0] == "GET" and c[1] == "/posts")
    assert get_posts[2].get("wpml_language") == "fr"
    assert "lang" not in get_posts[2]

    post_create = next(c for c in captured if c[0] == "POST" and c[1] == "/posts")
    assert post_create[2] == {"wpml_language": "fr"}
    assert ("lang", "fr") in meta_calls


def test_provider_none_omits_lang_query_params_but_sets_meta(mocker):
    client = WordPressClient(_wp_settings(provider=I18nProvider.NONE))
    captured: list[tuple[str, str, dict]] = []
    meta_calls: list[tuple[str, str]] = []

    def fake_request(method, path, **kwargs):
        key = path.split("?")[0]
        captured.append((method, key, dict(kwargs.get("params") or {})))
        if method == "GET" and key == "/posts":
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key == "/posts":
            return MagicMock(status_code=201, json=lambda: {"id": 100})
        if method == "POST" and key == "/posts/100/meta":
            body = kwargs.get("json") or {}
            meta_calls.append((body.get("key"), body.get("value")))
            return MagicMock(status_code=201, json=lambda: {})
        if method == "GET" and key in ("/tags", "/categories"):
            return MagicMock(status_code=200, json=lambda: [])
        if method == "POST" and key in ("/tags", "/categories"):
            return MagicMock(status_code=201, json=lambda: {"id": 1})
        return MagicMock(status_code=200, json=lambda: {})

    mocker.patch.object(client, "_request", side_effect=fake_request)

    client.publish_post(_sample_post(lang="fr"))

    get_posts = next(c for c in captured if c[0] == "GET" and c[1] == "/posts")
    assert "lang" not in get_posts[2]
    assert "wpml_language" not in get_posts[2]

    post_create = next(c for c in captured if c[0] == "POST" and c[1] == "/posts")
    assert post_create[2] == {}
    assert ("lang", "fr") in meta_calls


def test_probe_polylang_warns_when_endpoint_missing(mocker, caplog):
    import logging

    client = WordPressClient(_wp_settings(provider=I18nProvider.POLYLANG))
    mock_get = mocker.patch(
        "md2wp.sinks.wordpress.requests.get",
        return_value=MagicMock(status_code=404, text="not found"),
    )

    with caplog.at_level(logging.WARNING):
        client.probe_i18n_provider()

    mock_get.assert_called_once()
    assert mock_get.call_args[0][0] == "https://example.com/wp-json/pll/v1/languages"
    assert "Polylang REST" in caplog.text


def test_probe_polylang_skipped_when_provider_none(mocker):
    client = WordPressClient(_wp_settings(provider=I18nProvider.NONE))
    mock_get = mocker.patch("md2wp.sinks.wordpress.requests.get")
    client.probe_i18n_provider()
    mock_get.assert_not_called()

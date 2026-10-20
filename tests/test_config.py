from pathlib import Path

from md2wp.config import (
    DEFAULT_MARKDOWN_EXTENSIONS,
    I18nProvider,
    ImportMode,
    PostStatus,
    load_settings,
)


def test_cli_overrides_toml_and_env(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text(
        '[import]\nmode = "hugo-build"\nsource = "./toml-source"\nstatus = "publish"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("MD2WP_MODE", "markdown")
    monkeypatch.setenv("MD2WP_SOURCE", "/env/source")
    monkeypatch.setenv("MD2WP_STATUS", "private")

    settings = load_settings(
        config_path=config,
        mode=ImportMode.MARKDOWN,
        source=Path("/cli/source"),
        status=PostStatus.DRAFT,
    )

    assert settings.mode == ImportMode.MARKDOWN
    assert settings.source == Path("/cli/source")
    assert settings.status == PostStatus.DRAFT


def test_toml_overrides_env(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text(
        '[import]\nmode = "hugo-build"\nsource = "./from-toml"\nstatus = "publish"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("MD2WP_MODE", "markdown")
    monkeypatch.setenv("MD2WP_SOURCE", "/env/source")
    monkeypatch.setenv("MD2WP_STATUS", "private")
    monkeypatch.delenv("MD2WP_EXPORT_OUTPUT", raising=False)
    monkeypatch.delenv("EXPORT_DIRECTORY", raising=False)

    settings = load_settings(config_path=config)

    assert settings.mode == ImportMode.HUGO_BUILD
    assert settings.source == Path("./from-toml")
    assert settings.status == PostStatus.PUBLISH


def test_env_used_when_toml_unset(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")
    monkeypatch.setenv("MD2WP_MODE", "hugo-build")
    monkeypatch.setenv("MD2WP_SOURCE", "/env/posts")
    monkeypatch.setenv("MD2WP_STATUS", "private")

    settings = load_settings(config_path=config)

    assert settings.mode == ImportMode.HUGO_BUILD
    assert settings.source == Path("/env/posts")
    assert settings.status == PostStatus.PRIVATE


def test_legacy_mode_and_source_aliases(monkeypatch, tmp_path):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")
    monkeypatch.delenv("MD2WP_MODE", raising=False)
    monkeypatch.delenv("MD2WP_SOURCE", raising=False)
    monkeypatch.setenv("MARKDOWN_PARSER", "hugo_build")
    monkeypatch.setenv("MARKDOWN_DIRECTORY", "/legacy/md")

    settings = load_settings(config_path=config)

    assert settings.mode == ImportMode.HUGO_BUILD
    assert settings.source == Path("/legacy/md")


def test_legacy_normal_mode_alias(monkeypatch, tmp_path):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")
    monkeypatch.delenv("MD2WP_MODE", raising=False)
    monkeypatch.setenv("MARKDOWN_PARSER", "normal")

    settings = load_settings(config_path=config)

    assert settings.mode == ImportMode.MARKDOWN


def test_password_never_loaded_from_toml(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text(
        '[wordpress]\nurl = "https://example.com/wp-json/wp/v2"\n'
        'username = "admin"\npassword = "from-toml"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("MD2WP_WORDPRESS_PASSWORD", raising=False)
    monkeypatch.delenv("PASSWORD", raising=False)

    settings = load_settings(config_path=config)

    assert settings.wordpress_url == "https://example.com/wp-json/wp/v2"
    assert settings.wordpress_username == "admin"
    assert settings.wordpress_password == ""


def test_password_from_env(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[wordpress]\n", encoding="utf-8")
    monkeypatch.setenv("MD2WP_WORDPRESS_PASSWORD", "app-pass")

    settings = load_settings(config_path=config)

    assert settings.wordpress_password == "app-pass"


def test_export_output_from_md2wp_export_output(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")
    monkeypatch.setenv("MD2WP_EXPORT_OUTPUT", "/exports/posts.xml")
    monkeypatch.delenv("EXPORT_DIRECTORY", raising=False)

    settings = load_settings(config_path=config)

    assert settings.output == Path("/exports/posts.xml")


def test_export_output_legacy_export_directory(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")
    monkeypatch.delenv("MD2WP_EXPORT_OUTPUT", raising=False)
    monkeypatch.setenv("EXPORT_DIRECTORY", "/legacy/export.xml")

    settings = load_settings(config_path=config)

    assert settings.output == Path("/legacy/export.xml")


def test_export_output_prefers_new_env_over_legacy(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")
    monkeypatch.setenv("MD2WP_EXPORT_OUTPUT", "/new/export.xml")
    monkeypatch.setenv("EXPORT_DIRECTORY", "/legacy/export.xml")

    settings = load_settings(config_path=config)

    assert settings.output == Path("/new/export.xml")


def test_export_output_cli_overrides_toml_and_env(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text('[import]\noutput = "./toml-out.xml"\n', encoding="utf-8")
    monkeypatch.setenv("MD2WP_EXPORT_OUTPUT", "/env/export.xml")

    settings = load_settings(config_path=config, output=Path("/cli/out.xml"))

    assert settings.output == Path("/cli/out.xml")


def test_markdown_extensions_from_toml(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text(
        '[markdown]\nextensions = ["fenced_code", "toc"]\n',
        encoding="utf-8",
    )

    settings = load_settings(config_path=config)

    assert settings.markdown_extensions == ["fenced_code", "toc"]


def test_markdown_extensions_defaults_when_unset(tmp_path):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")

    settings = load_settings(config_path=config)

    assert settings.markdown_extensions == DEFAULT_MARKDOWN_EXTENSIONS


def test_i18n_defaults_when_unset(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[wordpress]\n", encoding="utf-8")
    monkeypatch.delenv("MD2WP_I18N_PROVIDER", raising=False)
    monkeypatch.delenv("MD2WP_I18N_LINK_TRANSLATIONS", raising=False)

    settings = load_settings(config_path=config)

    assert settings.wordpress_i18n.provider == I18nProvider.NONE
    assert settings.wordpress_i18n.link_translations is False


def test_i18n_from_toml(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text(
        '[wordpress.i18n]\nprovider = "polylang"\nlink_translations = true\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("MD2WP_I18N_PROVIDER", raising=False)
    monkeypatch.delenv("MD2WP_I18N_LINK_TRANSLATIONS", raising=False)

    settings = load_settings(config_path=config)

    assert settings.wordpress_i18n.provider == I18nProvider.POLYLANG
    assert settings.wordpress_i18n.link_translations is True


def test_i18n_toml_overrides_env(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text(
        '[wordpress.i18n]\nprovider = "wpml"\nlink_translations = false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("MD2WP_I18N_PROVIDER", "polylang")
    monkeypatch.setenv("MD2WP_I18N_LINK_TRANSLATIONS", "true")

    settings = load_settings(config_path=config)

    assert settings.wordpress_i18n.provider == I18nProvider.WPML
    assert settings.wordpress_i18n.link_translations is False


def test_i18n_from_env_when_toml_unset(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[wordpress]\n", encoding="utf-8")
    monkeypatch.setenv("MD2WP_I18N_PROVIDER", "polylang")
    monkeypatch.setenv("MD2WP_I18N_LINK_TRANSLATIONS", "1")

    settings = load_settings(config_path=config)

    assert settings.wordpress_i18n.provider == I18nProvider.POLYLANG
    assert settings.wordpress_i18n.link_translations is True


def test_i18n_env_link_translations_falsey(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[wordpress]\n", encoding="utf-8")
    monkeypatch.setenv("MD2WP_I18N_PROVIDER", "wpml")
    monkeypatch.setenv("MD2WP_I18N_LINK_TRANSLATIONS", "false")

    settings = load_settings(config_path=config)

    assert settings.wordpress_i18n.provider == I18nProvider.WPML
    assert settings.wordpress_i18n.link_translations is False

from pathlib import Path

from md2wp.config import CodeBlocksFormat, Settings, load_settings
from md2wp.content import wrap_code_blocks
from md2wp.parsers.markdown import discover_and_parse_markdown
from md2wp.pipeline import discover_and_parse

FIXTURES = Path(__file__).parent / "fixtures"


def test_wrap_fenced_python_adds_gutenberg_and_language():
    html = '<pre><code class="language-python">print("hello")\n</code></pre>'
    result = wrap_code_blocks(html)
    assert "<!-- wp:code" in result
    assert '{"language":"python"}' in result
    assert 'class="wp-block-code"' in result or "class='wp-block-code'" in result
    assert "language-python" in result
    assert "<!-- /wp:code -->" in result
    assert 'print("hello")' in result or "print(&quot;hello&quot;)" in result


def test_wrap_fence_without_language():
    html = "<pre><code>plain code</code></pre>"
    result = wrap_code_blocks(html)
    assert "<!-- wp:code -->" in result
    assert '{"language"' not in result
    assert "<!-- /wp:code -->" in result
    assert "plain code" in result


def test_wrap_idempotent_for_already_gutenberg():
    html = (
        '<!-- wp:code {"language":"go"} -->\n'
        '<pre class="wp-block-code"><code class="language-go">fmt.Println()</code></pre>\n'
        "<!-- /wp:code -->"
    )
    assert wrap_code_blocks(html) == wrap_code_blocks(wrap_code_blocks(html))
    once = wrap_code_blocks(html)
    assert once.count("<!-- wp:code") == 1
    assert once.count("<!-- /wp:code -->") == 1


def test_wrap_hugo_highlight_unwraps_and_uses_data_lang():
    html = (
        '<div class="highlight">'
        '<pre tabindex="0" class="chroma">'
        '<code class="language-rust" data-lang="rust">'
        '<span class="n">fn</span> main() {}'
        "</code></pre></div>"
    )
    result = wrap_code_blocks(html)
    assert "class=\"highlight\"" not in result and "class='highlight'" not in result
    assert "<!-- wp:code" in result
    assert '{"language":"rust"}' in result
    assert "language-rust" in result
    assert '<span class="n">fn</span>' in result or "<span class=\"n\">fn</span>" in result
    assert "wp-block-code" in result


def test_wrap_leaves_inline_code_alone():
    html = "<p>Use <code>print()</code> here.</p>"
    assert wrap_code_blocks(html) == html or "print()" in wrap_code_blocks(html)
    result = wrap_code_blocks(html)
    assert "<!-- wp:code" not in result
    assert "<p>" in result
    assert "<code>print()</code>" in result or "print()" in result


def test_parse_fixture_gets_gutenberg_via_pipeline():
    settings = Settings(
        source=FIXTURES,
        recursive=False,
        include_drafts=False,
        code_blocks=CodeBlocksFormat.GUTENBERG,
    )
    result = discover_and_parse(settings)
    assert not result.errors
    assert len(result.posts) == 1
    html = result.posts[0].html_content
    assert "<!-- wp:code" in html
    assert '{"language":"python"}' in html
    assert "language-python" in html


def test_classic_code_blocks_skips_wrap():
    settings = Settings(
        source=FIXTURES,
        recursive=False,
        include_drafts=False,
        code_blocks=CodeBlocksFormat.CLASSIC,
    )
    result = discover_and_parse(settings)
    html = result.posts[0].html_content
    assert "<!-- wp:code" not in html
    assert "<pre>" in html
    assert "language-python" in html


def test_markdown_parser_alone_still_classic():
    """Transform runs in pipeline, not in the raw markdown parser."""
    settings = Settings(recursive=False, include_drafts=False)
    posts, errors, _skipped = discover_and_parse_markdown(FIXTURES, settings)
    assert not errors
    assert "<!-- wp:code" not in posts[0].html_content
    assert "<pre>" in posts[0].html_content


def test_code_blocks_from_toml(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text('[content]\ncode_blocks = "classic"\n', encoding="utf-8")
    monkeypatch.delenv("MD2WP_CODE_BLOCKS", raising=False)

    settings = load_settings(config_path=config)
    assert settings.code_blocks == CodeBlocksFormat.CLASSIC


def test_code_blocks_from_env(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")
    monkeypatch.setenv("MD2WP_CODE_BLOCKS", "classic")

    settings = load_settings(config_path=config)
    assert settings.code_blocks == CodeBlocksFormat.CLASSIC


def test_code_blocks_default_gutenberg(tmp_path, monkeypatch):
    config = tmp_path / "md2wp.toml"
    config.write_text("[import]\n", encoding="utf-8")
    monkeypatch.delenv("MD2WP_CODE_BLOCKS", raising=False)

    settings = load_settings(config_path=config)
    assert settings.code_blocks == CodeBlocksFormat.GUTENBERG

"""Tests for the Quarto post-render step (report/scripts/postprocess.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "report" / "scripts" / "postprocess.py"


@pytest.fixture(scope="module")
def postprocess(tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    """Import the script with an empty output directory so its page loop does nothing."""
    empty = tmp_path_factory.mktemp("site")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("QUARTO_PROJECT_OUTPUT_DIR", str(empty))
        spec = importlib.util.spec_from_file_location("postprocess", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def test_head_scripts_are_deferred_but_body_scripts_are_not(postprocess: ModuleType) -> None:
    html = (
        '<head><script src="a.js"></script><script src="m.js" type="module"></script></head>'
        '<body><script src="b.js"></script></body>'
    )
    result = postprocess.defer_head_scripts(html)
    assert '<script src="a.js" defer></script>' in result
    assert '<script src="m.js" type="module"></script>' in result
    assert '<script src="b.js"></script>' in result


def test_inactive_colour_schemes_start_disabled(postprocess: ModuleType) -> None:
    active = '<link href="x.css" rel="stylesheet" class="quarto-color-scheme" id="s">'
    alternate = (
        '<link href="d.css" rel="stylesheet" append-hash="true" '
        'class="quarto-color-scheme quarto-color-alternate" id="s">'
    )
    extra = '<link href="x.css" rel="stylesheet" class="quarto-color-scheme-extra" id="s">'
    result = postprocess.INACTIVE_SCHEME.sub(
        r'rel="disabled-stylesheet"\1', active + alternate + extra
    )
    assert active in result
    assert result.count('rel="disabled-stylesheet"') == 2


def test_icons_are_inlined_and_icon_font_dropped(postprocess: ModuleType) -> None:
    html = (
        '<link href="site_libs/bootstrap/bootstrap-icons.css" rel="stylesheet">\n'
        '<a><i class="bi bi-github" role="img" aria-label="Source code">\n</i></a>'
        '<a><i class="bi bi-file-pdf"></i>PDF</a><button><i class="bi"></i></button>'
    )
    result = postprocess.inline_icons(html)
    assert "bootstrap-icons.css" not in result
    assert '<svg class="bi bi-github"' in result and 'aria-label="Source code"' in result
    assert '<svg class="bi bi-file-pdf"' in result and 'aria-hidden="true"' in result
    assert '<i class="bi"></i>' in result  # the dark-mode toggle keeps its CSS icon


def test_unknown_icon_keeps_the_font(postprocess: ModuleType) -> None:
    html = (
        '<link href="site_libs/bootstrap/bootstrap-icons.css" rel="stylesheet">\n'
        '<i class="bi bi-not-an-icon"></i>'
    )
    assert postprocess.inline_icons(html) == html

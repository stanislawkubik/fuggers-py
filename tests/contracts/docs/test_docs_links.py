from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT


def test_docs_do_not_contain_local_absolute_filesystem_links() -> None:
    markdown_paths = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]

    for path in markdown_paths:
        text = path.read_text(encoding="utf-8")
        assert "/Users/" not in text, f"{path} contains a local macOS absolute path"
        assert "C:\\" not in text, f"{path} contains a local Windows absolute path"
        assert "file://" not in text, f"{path} contains a local file URI"

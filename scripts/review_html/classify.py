"""Classify changed files as code, docs, or other.

The review skills used to state this rule in prose and ask the agent to apply
it; having the renderer apply it keeps the three skills consistent and makes
the per-file grouping reproducible.

``docs`` is documentation proper. ``other`` is what a reviewer neither reads
as prose nor as code: images, lockfiles, and editor or VCS dotfiles. Build
configuration, CI workflows, dependency manifests, and ``.txt`` files outside
``docs/`` are ``code``, because test results matter for them.
"""
from __future__ import annotations

from pathlib import PurePosixPath

KINDS = ("code", "docs", "other")

_DOC_EXTENSIONS = frozenset({".md", ".markdown", ".mdx", ".rst", ".adoc", ".asciidoc"})
_DOC_STEMS = frozenset({"readme", "changelog", "license", "licence", "contributing", "codeowners"})
_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp"})
_LOCKFILES = frozenset({
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "cargo.lock", "poetry.lock", "pipfile.lock", "uv.lock", "gemfile.lock", "composer.lock",
    "go.sum", "package.resolved", "flake.lock", "mix.lock", "pubspec.lock",
})
_DOTFILES = frozenset({".gitignore", ".gitattributes", ".gitkeep", ".gitmodules",
                       ".editorconfig", ".mailmap"})


def classify_path(path: str) -> str:
    """Return ``"code"``, ``"docs"``, or ``"other"`` for a repository path."""
    parts = PurePosixPath(path).parts
    name = parts[-1].lower() if parts else ""
    stem, dot, ext = name.rpartition(".")
    ext = "." + ext if dot else ""
    if "docs" in parts[:-1] or ext in _DOC_EXTENSIONS or (stem or name) in _DOC_STEMS:
        return "docs"
    if ext in _IMAGE_EXTENSIONS or name in _LOCKFILES or name.endswith(".lock") or name in _DOTFILES:
        return "other"
    return "code"


def file_kind(entry: dict) -> str:
    """The kind of a ``files[]`` entry: its explicit ``kind`` when valid, else derived."""
    kind = entry.get("kind")
    if kind in KINDS:
        return kind
    return classify_path(entry.get("path", ""))


def is_docs_only(files: list[dict]) -> bool:
    """True when no changed file is code. An empty list is not docs-only."""
    return bool(files) and all(file_kind(f) != "code" for f in files)

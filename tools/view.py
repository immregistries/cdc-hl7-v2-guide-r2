"""Reader and author views of the website.

The guide is for readers. Material for the authors (quality findings, comparisons with other documents, TA questions, how
the guide is made) is marked author-only and shown only in the author view. Nothing in it is secret; it is hidden because
readers do not need it.

Editions (tools/build_site.py --edition):

- draft    (default) the author view appears only when InteropHub confirms that the signed-in person is an author of the
           guide (permissions.isAuthor from the guide API: the same check that lets them dispose of and close comments).
           Everyone else sees the reader view, with no switch and no mention of it.
- author   the author view is always on, with the switch to the reader view (local previews and checks).
- release  author material is left out entirely, and the author pages are not built (formal releases).
"""

from __future__ import annotations

EDITIONS = ("draft", "author", "release")
_edition = "draft"


def set_edition(edition: str) -> None:
    global _edition
    if edition not in EDITIONS:
        raise ValueError(f"unknown edition {edition!r}; expected one of {', '.join(EDITIONS)}")
    _edition = edition


def edition() -> str:
    return _edition


def release() -> bool:
    return _edition == "release"


def author(fragment: str, tag: str = "div") -> str:
    """Author-only material: wrapped to be shown only in the author view, or left out of a release."""
    if not fragment or _edition == "release":
        return ""
    return f'<{tag} class="author-only">{fragment}</{tag}>'

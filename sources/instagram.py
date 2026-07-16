"""Instagram profile enumeration via instaloader.

Lazily imports instaloader so the rest of the sources layer works without it.
Returns video posts as :class:`MediaReference` items for the selection grid.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from sources.media_ref import MediaReference

log = logging.getLogger(__name__)


def username_from(source: str) -> str:
    """Extract an Instagram username from a URL, @handle, or bare name."""
    source = (source or "").strip()
    m = re.search(r"instagram\.com/([^/?#]+)", source)
    if m:
        return m.group(1)
    return source.lstrip("@")


def enumerate_profile(
    source: str,
    limit: int = 50,
    session_user: Optional[str] = None,
    session_file: Optional[str] = None,
) -> List[MediaReference]:
    """Return video posts of an Instagram profile as media references.

    ``session_user``/``session_file`` enable authenticated access to more posts;
    without them only public content is reachable.
    """
    try:
        import instaloader  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "instaloader is not installed. Run: pip install instaloader"
        ) from exc

    username = username_from(source)
    loader = instaloader.Instaloader(
        download_pictures=False, download_videos=False, download_comments=False,
        save_metadata=False, quiet=True,
    )
    if session_user:
        try:
            if session_file:
                loader.load_session_from_file(session_user, session_file)
            else:
                loader.load_session_from_file(session_user)
        except Exception as exc:  # pragma: no cover - auth is environment-specific
            log.warning("Could not load Instagram session: %s", exc)

    profile = instaloader.Profile.from_username(loader.context, username)
    refs: List[MediaReference] = []
    for post in profile.get_posts():
        if not getattr(post, "is_video", False):
            continue
        caption = (post.caption or "").strip().replace("\n", " ")
        refs.append(MediaReference(
            source_url=f"https://www.instagram.com/p/{post.shortcode}/",
            title=(caption[:60] or post.shortcode),
            duration=getattr(post, "video_duration", None),
            thumbnail=getattr(post, "url", "") or "",
            status="pending",
            meta={"shortcode": post.shortcode, "username": username},
        ))
        if len(refs) >= limit:
            break
    log.info("Instagram %s: %d video posts", username, len(refs))
    return refs


__all__ = ["enumerate_profile", "username_from"]

import logging
import os
import sys

from fastmcp import FastMCP
import yt_dlp

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

BASE_OPTS = {
    "format": "ba[protocol^=http]/ba/b",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
}


def soundcloud_resolve(search_term: str):
    """Search SoundCloud, then try each result until one is actually playable."""
    # Step 1: get a list of candidate track pages (fast, no stream extraction)
    with yt_dlp.YoutubeDL({**BASE_OPTS, "extract_flat": True}) as ydl:
        results = ydl.extract_info(f"scsearch8:{search_term}", download=False)
    candidates = [e for e in (results.get("entries") or []) if e and e.get("url")]

    # Step 2: try each candidate, skipping DRM / previews / failures
    for entry in candidates:
        try:
            with yt_dlp.YoutubeDL(BASE_OPTS) as ydl:
                info = ydl.extract_info(entry["url"], download=False)
            duration = info.get("duration") or 0
            if info.get("url") and duration > 60:  # skip 30s previews
                return info
            logger.info(f"Skipping short/preview track: {info.get('title')}")
        except Exception as e:
            logger.info(f"Skipping '{entry.get('title', entry['url'])}': {e}")
    return None


def youtube_resolve(search_term: str):
    opts = dict(BASE_OPTS)
    if os.path.isfile(COOKIE_FILE):
        opts["cookiefile"] = COOKIE_FILE
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{search_term}", download=False)
    entries = info.get("entries") or [info]
    return entries[0] if entries else None


@mcp.tool()
def resolve_music_url(query: str, artist: str = "") -> dict:
    """Search for a song and return a direct, playable audio stream URL."""
    search_term = f"{artist} {query}".strip()
    logger.info(f"Resolving track for query: {search_term}")

    top = None
    last_error = None

    for name, fn in (("soundcloud", soundcloud_resolve), ("youtube", youtube_resolve)):
        try:
            top = fn(search_term)
            if top and top.get("url"):
                logger.info(f"Found via {name}: {top.get('title')}")
                break
        except Exception as e:
            last_error = e
            logger.error(f"{name} failed: {e}")

    if not top or not top.get("url"):
        return {
            "status": "error",
            "message": str(last_error) if last_error else f"No playable result for '{search_term}'",
        }

    return {
        "status": "success",
        "url": top["url"],
        "audio_url": top["url"],
        "title": top.get("title", search_term),
        "artist": top.get("uploader", "Unknown"),
        "duration": top.get("duration"),
        "type": "audio",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

import logging
import os
import sys

from fastmcp import FastMCP
import yt_dlp

# Log to stderr so stdout stays clean for the MCP protocol
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")


def extract(search_term: str, source: str, use_cookies: bool):
    ydl_opts = {
        "format": "ba[protocol^=http]/ba/b",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if use_cookies and os.path.isfile(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"{source}:{search_term}", download=False)
        entries = info.get("entries") or [info]
        return entries[0] if entries else None


@mcp.tool()
def resolve_music_url(query: str, artist: str = "") -> dict:
    """Search for a song and return a direct, playable audio stream URL."""
    search_term = f"{artist} {query}".strip()
    logger.info(f"Resolving track for query: {search_term}")

    last_error = None
    # SoundCloud first (works from servers), then YouTube as a fallback
    attempts = [("scsearch1", False), ("ytsearch1", True), ("ytsearch1", False)]

    for source, use_cookies in attempts:
        try:
            top = extract(search_term, source, use_cookies)
            if top and top.get("url"):
                return {
                    "status": "success",
                    "url": top["url"],
                    "audio_url": top["url"],
                    "title": top.get("title", search_term),
                    "artist": top.get("uploader", "Unknown"),
                    "duration": top.get("duration"),
                    "type": "audio",
                }
        except Exception as e:
            last_error = e
            logger.error(f"{source} failed (cookies={use_cookies}): {e}")

    return {
        "status": "error",
        "message": str(last_error) if last_error else f"No results for '{search_term}'",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

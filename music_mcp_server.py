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


def extract(search_term: str, use_cookies: bool):
    ydl_opts = {
        "format": "ba/b",  # any audio, or any format as a last resort
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if use_cookies and os.path.isfile(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{search_term}", download=False)
        entries = info.get("entries") or [info]
        return entries[0] if entries else None


@mcp.tool()
def resolve_music_url(query: str, artist: str = "") -> dict:
    """Search YouTube for a song and return a direct, playable audio stream URL."""
    search_term = f"{artist} {query}".strip()
    logger.info(f"Resolving track for query: {search_term}")

    top = None
    last_error = None

    # Try with cookies first, then without (bad cookies can break extraction)
    for use_cookies in (True, False):
        try:
            top = extract(search_term, use_cookies)
            if top and top.get("url"):
                break
        except Exception as e:
            last_error = e
            logger.error(f"Extraction error (cookies={use_cookies}): {e}")

    if not top or not top.get("url"):
        return {
            "status": "error",
            "message": str(last_error) if last_error else f"No results for '{search_term}'",
        }

    return {
        "status": "success",
        "url": top["url"],
        "audio_url": top["url"],
        "title": top.get("title", search_term),
        "artist": top.get("uploader", "YouTube"),
        "duration": top.get("duration"),
        "type": "audio",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

import logging
import os
import sys

from fastmcp import FastMCP
import yt_dlp

# Log to stderr so stdout stays clean for the MCP stdio protocol
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")


@mcp.tool()
def resolve_music_url(query: str, artist: str = "") -> dict:
    """Search YouTube for a song and return a direct, playable audio stream URL."""
    search_term = f"{artist} {query}".strip()

    ydl_opts = {
        # Prefer m4a/AAC: widely supported by embedded players
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        # NOTE: no extract_flat, we need the real stream URL
    }
    if os.path.isfile(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE

    try:
        logger.info(f"Resolving track for query: {search_term}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{search_term}", download=False)

            entries = info.get("entries") or [info]
            top = entries[0] if entries else None
            if not top:
                return {"status": "error", "message": f"No results for '{search_term}'"}

            stream_url = top.get("url")
            if not stream_url:
                return {"status": "error", "message": "Could not extract a stream URL"}

            return {
                "status": "success",
                "url": stream_url,
                "audio_url": stream_url,
                "title": top.get("title", search_term),
                "artist": top.get("uploader", "YouTube"),
                "duration": top.get("duration"),
                "type": "audio",
            }
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")

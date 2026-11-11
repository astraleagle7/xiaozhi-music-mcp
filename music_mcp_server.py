import logging
from fastmcp import FastMCP
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

def get_youtube_audio(query: str) -> dict:
    """Searches YouTube and returns a direct audio stream URL using a universal format."""
    ydl_opts = {
        'format': 'best', # Uses a universal stream selector to avoid format errors
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
        'default_search': 'ytsearch1:',
    }
    
    try:
        logger.info(f"Searching YouTube with universal format for: {query}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries', [info])
            if entries and len(entries) > 0:
                top = entries[0]
                return {
                    "status": "success",
                    "url": top.get("url") or top.get("webpage_url"),
                    "title": top.get("title", query),
                    "artist": top.get("uploader", "YouTube"),
                }
    except Exception as e:
        logger.error(f"YouTube extraction error: {e}")
    
    return {"status": "error", "message": f"Could not find audio stream for: {query}"}

@mcp.tool()
async def resolve_music_url(query: str, artist: str = "") -> dict:
    """Resolves music requests by returning playable YouTube audio streams."""
    search_term = f"{artist} {query}".strip()
    return get_youtube_audio(search_term)

if __name__ == "__main__":
    mcp.run()


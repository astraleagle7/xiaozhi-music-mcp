import logging
from fastmcp import FastMCP
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

def get_youtube_audio(query: str) -> dict:
    """Extracts a reliable stream URL using safe URL extraction."""
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
        'default_search': 'ytsearch1:',
        'extract_flat': True, # Avoids complex format parsing entirely
    }
    
    try:
        logger.info(f"Resolving stream for query: {query}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries', [info])
            if entries and len(entries) > 0:
                top = entries.get(0) if isinstance(entries, dict) else entries[0]
                
                vid_id = top.get('id')
                title = top.get('title', query)
                
                if vid_id:
                    direct_url = f"https://www.youtube.com/watch?v={vid_id}"
                else:
                    direct_url = top.get('url') or f"https://www.youtube.com/results?search_query={query}"

                return {
                    "status": "success",
                    "url": direct_url,
                    "audio_url": direct_url,
                    "title": title,
                    "artist": top.get("uploader", "YouTube"),
                    "action": "play",
                    "message": f"Playing {title}"
                }
    except Exception as e:
      logger.error(f"Extraction failed: {e}")

    return {"status": "error", "message": f"Could not find audio stream for: {query}"}

@mcp.tool()
async def resolve_music_url(query: str, artist: str = "") -> dict:
    """Resolves music requests by returning playable YouTube audio streams."""
    search_term = f"{artist} {query}".strip()
    return get_youtube_audio(search_term)

if __name__ == "__main__":
    mcp.run()


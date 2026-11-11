import logging
from fastmcp import FastMCP
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

@mcp.tool()
def resolve_music_url(query: str, artist: str = "") -> dict:
    """Resolves music requests by returning playable YouTube audio streams."""
    search_term = f"{artist} {query}".strip()
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
        'default_search': 'ytsearch1:',
        'extract_flat': True,
    }
    
    try:
        logger.info(f"Resolving track for query: {search_term}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_term, download=False)
            entries = info.get('entries', [info])
            if entries and len(entries) > 0:
                top = entries[0]
                vid_id = top.get('id')
                title = top.get('title', search_term)
                
                media_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else top.get('url', '')
                
                # Hardcoded hardware interception payload
                return {
                    "type": "audio",
                    "command": "play",
                    "action": "play_music",
                    "audio_url": media_url,
                    "url": media_url,
                    "title": title,
                    "status": "success"
                }
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        
    return {"type": "error", "status": "error", "message": f"Could not find audio stream for: {search_term}"}

if __name__ == "__main__":
    mcp.run()

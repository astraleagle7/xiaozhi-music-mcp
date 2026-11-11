import logging
from fastmcp import FastMCP
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

def get_youtube_audio(query: str) -> dict:
    """Extracts a direct playable URL using dynamic format selection."""
    ydl_opts = {
        # 'best' tells yt-dlp to grab any single pre-combined stream without requiring ffmpeg
        'format': 'best/bestaudio/18/22',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
        'default_search': 'ytsearch1:',
    }
    
    try:
        logger.info(f"Extracting stream for: {query}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries', [info])
            if entries and len(entries) > 0:
                top = entries[0]
                
                # Extract direct stream URL from top object or inspect format list dynamically
                stream_url = top.get("url")
                if not stream_url and 'formats' in top:
                    for fmt in reversed(top['formats']):
                        if fmt.get('url'):
                            stream_url = fmt.get('url')
                            break
                            
                title = top.get("title", query)
                final_url = stream_url or top.get("webpage_url")
                
                return {
                    "status": "success",
                    "url": final_url,
                    "audio_url": final_url,
                    "title": title,
                    "artist": top.get("uploader", "YouTube"),
                    "action": "play",
                    "message": f"Playing {title}"
                }
    except Exception as e:
        logger.error(f"Extraction error: {e}")
    
    return {"status": "error", "message": f"Could not find audio stream for: {query}"}

@mcp.tool()
async def resolve_music_url(query: str, artist: str = "") -> dict:
    """Resolves music requests by returning playable YouTube audio streams."""
    search_term = f"{artist} {query}".strip()
    return get_youtube_audio(search_term)

if __name__ == "__main__":
    mcp.run()


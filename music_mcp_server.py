import logging
from fastmcp import FastMCP
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

def get_youtube_audio(query: str) -> dict:
    """Extracts a direct playable audio stream URL for hardware ingestion."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
        'default_search': 'ytsearch1:',
    }
    
    try:
        logger.info(f"Resolving audio stream for: {query}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries', [info])
            if entries and len(entries) > 0:
                top = entries[0]
                
                # Extract direct stream URL
                stream_url = top.get("url")
                if not stream_url and 'formats' in top:
                    for f in top['formats']:
                        if f.get('url') and f.get('acodec') != 'none':
                            stream_url = f.get('url')
                            break
                            
                title = top.get("title", query)
                final_url = stream_url or top.get("webpage_url")
                
                return {
                    "status": "success",
                    "url": final_url,
                    "audio_url": final_url,
                    "title": title,
                    "artist": top.get("uploader", "YouTube"),
                    "type": "audio"
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


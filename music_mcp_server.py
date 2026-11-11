import logging
from fastmcp import FastMCP
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

def get_youtube_audio(query: str) -> str:
    """Extracts a reliable stream URL and returns a command string for the agent."""
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
        'default_search': 'ytsearch1:',
        'extract_flat': True,
    }
    
    try:
        logger.info(f"Resolving stream for query: {query}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries', [info])
            if entries and len(entries) > 0:
                top = entries[0]
                vid_id = top.get('id')
                title = top.get('title', query)
                
                if vid_id:
                    direct_url = f"https://www.youtube.com/watch?v={vid_id}"
                else:
                    direct_url = top.get('url') or f"https://www.youtube.com/results?search_query={query}"

                # Returns an explicit instruction string for the LLM
                return f"PLAY_URL: {direct_url} | TITLE: {title}"
    except Exception as e:
        logger.error(f"Extraction failed: {e}")

    return "ERROR: Could not find audio stream."

@mcp.tool()
async def resolve_music_url(query: str, artist: str = "") -> str:
    """Resolves music requests by returning playable YouTube audio streams."""
    search_term = f"{artist} {query}".strip()
    return get_youtube_audio(search_term)

if __name__ == "__main__":
    mcp.run()


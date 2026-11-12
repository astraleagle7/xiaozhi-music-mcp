import contextlib
import logging
import os
import sys

from fastmcp import FastMCP
import yt_dlp
import tinytuya

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("xiaozhi-music-resolver")

mcp = FastMCP("xiaozhi-music-resolver")

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

if os.environ.get("COOKIES_TXT") and not os.path.isfile(COOKIE_FILE):
    with open(COOKIE_FILE, "w") as f:
        f.write(os.environ["COOKIES_TXT"])

# ---------------------------------------------------------------------------
# MUSIC
# ---------------------------------------------------------------------------

BASE_OPTS = {
    "format": "ba[ext=mp3][protocol^=http]/ba[protocol^=http]/ba/b",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
}


def soundcloud_resolve(search_term: str):
    with yt_dlp.YoutubeDL({**BASE_OPTS, "extract_flat": True}) as ydl:
        results = ydl.extract_info(f"scsearch8:{search_term}", download=False)
    candidates = [e for e in (results.get("entries") or []) if e and e.get("url")]

    for entry in candidates:
        try:
            with yt_dlp.YoutubeDL(BASE_OPTS) as ydl:
                info = ydl.extract_info(entry["url"], download=False)
            duration = info.get("duration") or 0
            if info.get("url") and duration > 60:
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
                logger.info(f"Stream URL: {top['url']}")
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
        "command": "play",
        "audio_url": top["url"],
        "url": top["url"],
        "title": top.get("title", search_term),
        "artist": top.get("uploader", "Unknown"),
        "type": "audio",
    }


# ---------------------------------------------------------------------------
# SMART HOME (Smart Life / Tuya cloud)
# ---------------------------------------------------------------------------

_cloud = None
_devices_cache = []

POWER_CODES = ("switch", "switch_1", "switch_led", "switch_go")


def get_cloud():
    global _cloud
    if _cloud is None:
        with contextlib.redirect_stdout(sys.stderr):
            _cloud = tinytuya.Cloud(
                apiRegion=os.environ.get("TUYA_REGION", "in"),
                apiKey=os.environ["TUYA_ACCESS_ID"],
                apiSecret=os.environ["TUYA_ACCESS_SECRET"],
                apiDeviceID=os.environ.get("TUYA_DEVICE_ID"),
            )
    return _cloud


def load_devices(force: bool = False):
    global _devices_cache
    if force or not _devices_cache:
        with contextlib.redirect_stdout(sys.stderr):
            result = get_cloud().getdevices()
        if not isinstance(result, list):
            raise RuntimeError(f"Could not load devices: {result}")
        _devices_cache = result
    return _devices_cache


def find_device(name: str):
    needle = name.lower().strip()
    for force in (False, True):
        for d in load_devices(force):
            if needle in str(d.get("name", "")).lower():
                return d
    return None


def device_status(device_id: str):
    with contextlib.redirect_stdout(sys.stderr):
        result = get_cloud().getstatus(device_id)
    return result.get("result", []) if isinstance(result, dict) else []


def send(device_id: str, code: str, value):
    with contextlib.redirect_stdout(sys.stderr):
        result = get_cloud().sendcommand(
            device_id, {"commands": [{"code": code, "value": value}]}
        )
    ok = isinstance(result, dict) and result.get("success")
    return {"status": "success" if ok else "error", "detail": result}


@mcp.tool()
def list_home_devices() -> dict:
    """List all Smart Life devices (lights, plugs, vacuum, etc.) with their names."""
    try:
        devices = load_devices(force=True)
        return {
            "status": "success",
            "devices": [
                {"name": d.get("name"), "id": d.get("id"), "online": d.get("online")}
                for d in devices
            ],
        }
    except Exception as e:
        logger.error(f"list_home_devices failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_device_status(device_name: str) -> dict:
    """Get the current status and available control codes of a Smart Life device."""
    try:
        d = find_device(device_name)
        if not d:
            return {"status": "error", "message": f"No device named '{device_name}'"}
        return {"status": "success", "name": d.get("name"), "state": device_status(d["id"])}
    except Exception as e:
        logger.error(f"get_device_status failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def set_power(device_name: str, on: bool) -> dict:
    """Turn a Smart Life device on or off (lights, plugs, and vacuum start/stop)."""
    try:
        d = find_device(device_name)
        if not d:
            return {"status": "error", "message": f"No device named '{device_name}'"}
        codes = [s.get("code") for s in device_status(d["id"])]
        code = next((c for c in POWER_CODES if c in codes), None)
        if not code:
            return {"status": "error", "message": f"No power switch found. Codes: {codes}"}
        return send(d["id"], code, bool(on))
    except Exception as e:
        logger.error(f"set_power failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def control_device(device_name: str, code: str, value: str) -> dict:
    """Send any control code to a device, e.g. code='switch_go' value='true'.
    Use get_device_status first to see which codes a device supports."""
    try:
        d = find_device(device_name)
        if not d:
            return {"status": "error", "message": f"No device named '{device_name}'"}
        v = value.strip()
        if v.lower() in ("true", "false"):
            parsed = v.lower() == "true"
        elif v.lstrip("-").isdigit():
            parsed = int(v)
        else:
            parsed = v
        return send(d["id"], code, parsed)
    except Exception as e:
        logger.error(f"control_device failed: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")

import os
import sys
import asyncio
import logging
import subprocess
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCP_PIPE")

async def run_pipe():
    uri = os.environ.get("MCP_ENDPOINT")
    if not uri:
        logger.error("Error: MCP_ENDPOINT environment variable is not set!")
        sys.exit(1)

    while True:
        try:
            logger.info("Connecting to Xiaozhi MCP endpoint...")
            async with websockets.connect(uri) as websocket:
                logger.info("Successfully connected to Xiaozhi cloud WebSocket!")

                cmd = [sys.executable, "music_mcp_server.py"]
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                logger.info("Started local music MCP server subprocess.")

                async def ws_to_proc():
                    async for message in websocket:
                        process.stdin.write(message + "\n")
                        process.stdin.flush()

                async def proc_to_ws():
                    while True:
                        line = await asyncio.to_thread(process.stdout.readline)
                        if not line:
                            break
                        await websocket.send(line.strip())

                async def stderr_to_log():
                    while True:
                        err = await asyncio.to_thread(process.stderr.readline)
                        if not err:
                            break
                        logger.error(f"[Server Error] {err.strip()}")

                await asyncio.gather(ws_to_proc(), proc_to_ws(), stderr_to_log())

        except Exception as e:
            logger.warning(f"Connection dropped: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_pipe())



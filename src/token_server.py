"""Token endpoint + static file server for the web client.

Routes:
  GET /token?room=<room>&identity=<identity>  → {"token": "<jwt>", "url": "<livekit_url>"}
  GET /                                        → web/index.html
  GET /<file>                                  → web/<file>

No auth, no user system — single-student MVP.
Run: .venv/bin/python src/token_server.py
"""

import os
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv
from livekit.api import AccessToken, CreateAgentDispatchRequest, LiveKitAPI, VideoGrants

load_dotenv(".env.local")

LIVEKIT_URL = os.environ["LIVEKIT_URL"]
LIVEKIT_API_KEY = os.environ["LIVEKIT_API_KEY"]
LIVEKIT_API_SECRET = os.environ["LIVEKIT_API_SECRET"]

DEFAULT_ROOM = "saathi-room"
DEFAULT_IDENTITY = "student"
AGENT_NAME = "haathi-mera-saathi"
WEB_DIR = Path(__file__).parent.parent / "web"


async def token_handler(request: web.Request) -> web.Response:
    room = request.rel_url.query.get("room", DEFAULT_ROOM)
    identity = request.rel_url.query.get("identity", DEFAULT_IDENTITY)

    token = (
        AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(VideoGrants(room_join=True, room=room))
        .to_jwt()
    )

    # Dispatch the agent to the room so it auto-joins when the student connects.
    # Fires once per token request; LiveKit deduplicates if an agent is already present.
    async with LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as lk:
        try:
            await lk.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(agent_name=AGENT_NAME, room=room)
            )
        except Exception as e:
            # Non-fatal: agent may already be in the room, or worker not yet connected.
            print(f"[dispatch] {e}")

    return web.json_response(
        {"token": token, "url": LIVEKIT_URL},
        headers={"Access-Control-Allow-Origin": "*"},
    )


async def index_handler(request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEB_DIR / "index.html")


app = web.Application()
app.router.add_get("/token", token_handler)
app.router.add_get("/", index_handler)
app.router.add_static("/", path=WEB_DIR, show_index=False)

if __name__ == "__main__":
    port = int(os.environ.get("TOKEN_PORT", 8080))
    print(f"Token server  →  http://localhost:{port}")
    print(f"Web client    →  http://localhost:{port}/")
    print(f"Token API     →  http://localhost:{port}/token")
    web.run_app(app, host="0.0.0.0", port=port, print=None)

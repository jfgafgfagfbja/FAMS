"""May chu thu cho ban Flutter web khi phat trien tren mot may.

Phuc vu thu muc build/web va chuyen tiep /api/* sang backend - giong cach nginx lam
trong docker-compose, nho vay trinh duyet thay web va API cung mot dia chi (khong vuong
CORS, va cookie/camera hoat dong dung nhu khi trien khai that).

Chay:
    python tool/web_proxy.py
Truoc do nho build web:
    flutter build web --release --dart-define=API_BASE_URL=/api

Bien moi truong tuy chon:
    FAMS_BACKEND   dia chi backend, mac dinh http://127.0.0.1:8000 (backend trong Docker)
    FAMS_WEB_DIR   thu muc web da build, mac dinh <mobile>/build/web
    FAMS_WEB_PORT  cong phuc vu, mac dinh 5180
"""
import os

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, Response
from starlette.routing import Route

MOBILE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.environ.get("FAMS_WEB_DIR") or os.path.join(MOBILE_DIR, "build", "web")
BACKEND = os.environ.get("FAMS_BACKEND", "http://127.0.0.1:8000")
PORT = int(os.environ.get("FAMS_WEB_PORT", "5180"))

# Cac tieu de chi co y nghia tren 1 chang ket noi, khong duoc chuyen tiep nguyen si.
HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
              "proxy-authorization", "proxy-authenticate", "host", "content-length",
              "content-encoding"}

client = httpx.AsyncClient(base_url=BACKEND, timeout=120)


async def api_proxy(request: Request) -> Response:
    path = request.path_params["path"]
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    upstream = await client.request(
        request.method, f"/{path}", params=request.query_params, headers=headers,
        content=await request.body(),
    )
    out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP}
    return Response(upstream.content, status_code=upstream.status_code, headers=out_headers)


async def static_files(request: Request) -> Response:
    rel = request.path_params.get("path", "") or "index.html"
    full = os.path.realpath(os.path.join(WEB_DIR, rel))
    # Chan thoat ra ngoai thu muc web, va tra index.html cho moi duong dan cua router.
    if not full.startswith(os.path.realpath(WEB_DIR)) or not os.path.isfile(full):
        full = os.path.join(WEB_DIR, "index.html")
    headers = {"Cache-Control": "no-cache"} if full.endswith((".html", ".js", ".json")) else {}
    return FileResponse(full, headers=headers)


app = Starlette(routes=[
    Route("/api/{path:path}", api_proxy,
          methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]),
    Route("/", static_files),
    Route("/{path:path}", static_files),
])

if __name__ == "__main__":
    if not os.path.isfile(os.path.join(WEB_DIR, "index.html")):
        raise SystemExit(
            f"Khong thay {os.path.join(WEB_DIR, 'index.html')}.\n"
            "Hay build truoc: flutter build web --release --dart-define=API_BASE_URL=/api"
        )
    print(f"Web: {WEB_DIR}\nAPI: {BACKEND}\nMo http://localhost:{PORT}")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

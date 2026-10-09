"""Chay giao dien web va API tren CUNG mot cong, trong CUNG mot tien trinh.

Dung cho noi chi mo duoc dung mot cong va khong chay duoc nginx rieng - vi du Hugging
Face Spaces (mot container, mot cong, chay bang user thuong nen nginx rat kho dung).
Hanh vi giong het nginx trong docker-compose:

    /api/...    -> backend FastAPI (bo tien to /api), giong `location /api/` cua nginx
    con lai     -> tep tinh cua ban Flutter web da build

App Flutter dung dinh tuyen bang dau # (/#/login) nen moi duong dan deu tra ve
index.html o goc, khong can quy tac du phong nhu try_files cua nginx.

Chay:
    WEB_DIR=/duong/dan/build/web uvicorn single_port:app --host 0.0.0.0 --port 7860 \
        --proxy-headers --forwarded-allow-ips "*"
"""
import os

from starlette.staticfiles import StaticFiles

from app.main import app as api

WEB_DIR = os.environ.get("WEB_DIR", os.path.join(os.path.dirname(__file__), "web"))
API_PREFIX = "/api"

if not os.path.isfile(os.path.join(WEB_DIR, "index.html")):
    raise RuntimeError(f"Khong thay ban web da build tai {WEB_DIR} (thieu index.html)")

_web = StaticFiles(directory=WEB_DIR, html=True)

# Ten tep cua ban build Flutter khong doi giua cac lan build (main.dart.js, index.html...).
# Khong dan Cache-Control thi trinh duyet tu giu ban cu mot thoi gian rat lau, cap nhat
# xong nguoi dung van thay giao dien cu. "no-cache" = moi lan dung phai hoi lai may chu;
# tep chua doi thi may chu tra 304 (khong tai lai), nen gan nhu khong ton them gi.
_REVALIDATE = (".html", ".js", ".mjs", ".json", ".wasm")


async def _web_always_fresh(scope, receive, send):
    path = scope.get("path", "")
    if not (path.endswith("/") or path.endswith(_REVALIDATE)):
        await _web(scope, receive, send)
        return

    async def send_no_cache(message):
        if message["type"] == "http.response.start":
            headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"cache-control"]
            headers.append((b"cache-control", b"no-cache"))
            message = {**message, "headers": headers}
        await send(message)

    await _web(scope, receive, send_no_cache)


async def app(scope, receive, send):
    # Su kien khoi dong/tat phai den backend: no khoi tao CSDL va chay cac tac vu nen
    # (tu dong dong phien qua han, don anh bang chung cu). Gui nham sang StaticFiles
    # thi cac tac vu do khong bao gio chay.
    if scope["type"] == "lifespan":
        await api(scope, receive, send)
        return

    path = scope.get("path", "")
    if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
        inner = dict(scope)
        inner["path"] = path[len(API_PREFIX):] or "/"
        raw = scope.get("raw_path")
        if raw is not None:
            inner["raw_path"] = raw[len(API_PREFIX):] or b"/"
        await api(inner, receive, send)
        return

    await _web_always_fresh(scope, receive, send)

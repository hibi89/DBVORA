"""Local-only, read-only FastAPI adapter for an explicitly selected SQLite file."""
from pathlib import Path

from dbvora.connectors.sqlite_reader import validate_path
from dbvora.errors import InventoryError
from dbvora.inventory import inspect_sqlite

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import FileResponse, JSONResponse
except ImportError as exc:
    raise RuntimeError('Install the local UI extra: python -m pip install -e ".[ui]"') from exc

WEB = Path(__file__).resolve().parent / 'web'


def create_app(db_path: str | Path, port: int = 8765) -> FastAPI:
    if not (1 <= port <= 65535):
        raise ValueError('Port must be between 1 and 65535.')
    # Fail before the server starts; never create/scan/open arbitrary files from HTTP.
    selected, _, _ = validate_path(db_path)
    app = FastAPI(title='DBVORA local viewer', docs_url=None, redoc_url=None, openapi_url=None)
    allowed_hosts = {f'127.0.0.1:{port}', '127.0.0.1', f'localhost:{port}', 'localhost'}
    allowed_origins = {f'http://127.0.0.1:{port}', f'http://localhost:{port}'}

    @app.middleware('http')
    async def localhost_guard(request: Request, call_next):
        host = request.headers.get('host', '')
        origin = request.headers.get('origin')
        fetch_site = request.headers.get('sec-fetch-site', '')
        if host not in allowed_hosts or (origin is not None and origin not in allowed_origins) or fetch_site == 'cross-site':
            response = JSONResponse(status_code=403, content={'error': {'code': 'FORBIDDEN', 'message': 'Local request required.'}})
        elif request.method not in ('GET', 'HEAD'):
            response = JSONResponse(status_code=405, content={'error': {'code': 'METHOD_NOT_ALLOWED', 'message': 'Read-only endpoint.'}})
        else:
            response = await call_next(request)
        response.headers.update({
            'Cache-Control': 'no-store',
            'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer',
            'X-Frame-Options': 'DENY',
            'Cross-Origin-Resource-Policy': 'same-origin',
            'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; font-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        })
        return response

    @app.get('/')
    async def home():
        return FileResponse(WEB / 'index.html', media_type='text/html; charset=utf-8')

    @app.get('/assets/app.js')
    async def app_script():
        return FileResponse(WEB / 'app.js', media_type='text/javascript; charset=utf-8')

    @app.get('/assets/style.css')
    async def app_style():
        return FileResponse(WEB / 'style.css', media_type='text/css; charset=utf-8')

    @app.get('/api/inventory')
    async def inventory():
        try:
            return JSONResponse(inspect_sqlite(selected))
        except InventoryError as exc:
            # No source path, SQLite SQL, query strings or stack traces in error responses.
            return JSONResponse(status_code=422, content={'error': {'code': exc.code, 'message': exc.message}})

    @app.get('/health')
    async def health():
        return JSONResponse({'ok': True, 'mode': 'local-read-only'})

    return app

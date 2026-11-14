"""Local-only, read-only FastAPI adapter for an explicitly selected SQLite file."""
from pathlib import Path
import stat
import hashlib

from dbvora.connectors.sqlite_reader import validate_path
from dbvora.errors import InventoryError
from dbvora.inventory import inspect_sqlite
from dbvora.observation_ledger import ObservationError, read_observations
from dbvora.storage_metrics import collect_table_storage
from dbvora.workspace import MAX_DATABASES, inspect_workspace

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import FileResponse, JSONResponse
except ImportError as exc:
    raise RuntimeError('Install the local UI extra: python -m pip install -e ".[ui]"') from exc

WEB = Path(__file__).resolve().parent / 'web'


def create_app(db_path: str | Path | list[str | Path] | tuple[str | Path, ...], port: int = 8765, *, observation_ledger_path: str | Path | None = None) -> FastAPI:
    if not (1 <= port <= 65535):
        raise ValueError('Port must be between 1 and 65535.')
    # The CLI selects every source at startup. No HTTP path/SQL input is
    # accepted. Preserve the one-database response contract verbatim.
    multi = isinstance(db_path, (list, tuple))
    if multi:
        if not 2 <= len(db_path) <= MAX_DATABASES:
            raise InventoryError('INVALID_DATABASE_COUNT', 'Select between 2 and 8 distinct SQLite databases.')
        selected_paths = tuple(validate_path(item)[0] for item in db_path)
        physical_ids = [(p.stat().st_dev, p.stat().st_ino) for p in selected_paths]
        if len(set(physical_ids)) != len(physical_ids):
            raise InventoryError('DUPLICATE_DATABASE', 'Select distinct SQLite files.')
        selected = None
    else:
        selected, _, _ = validate_path(db_path)
        selected_paths = (selected,)
    by_db_id = {hashlib.sha256(str(p).encode('utf-8')).hexdigest()[:24]: p
                for p in selected_paths}
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
            # Reuse the existing safe multi-workspace limit (2-8 databases,
            # <=2000 total tables), but skip eager per-table dbstat scans.
            report = (inspect_workspace(selected_paths, measure_table_storage=False)
                      if multi else inspect_sqlite(selected))
            return JSONResponse(report)
        except InventoryError as exc:
            # No source path, SQLite SQL, query strings or stack traces in error responses.
            return JSONResponse(status_code=422, content={'error': {'code': exc.code, 'message': exc.message}})

    @app.get('/api/table-storage')
    async def table_storage(request: Request):
        """Opt-in, bounded measurement only; no DB rows or arbitrary SQL."""
        names = request.query_params.getlist('table')
        database_ids = request.query_params.getlist('database')
        expected_keys = {'table', 'database'} if multi else {'table'}
        if (len(names) != 1 or not names[0] or len(names[0]) > 512
                or '\x00' in names[0]
                or set(request.query_params.keys()) != expected_keys
                or (multi and (len(database_ids) != 1
                               or database_ids[0] not in by_db_id))
                or (not multi and database_ids)):
            return JSONResponse(status_code=422, content={
                'error': {'code': 'INVALID_TABLE', 'message': 'Select a valid table.'}})
        name = names[0]
        target = by_db_id[database_ids[0]] if multi else selected
        try:
            initial = target.lstat()
            inventory = inspect_sqlite(target)
            table = next((item for item in inventory['tables'] if item['name'] == name), None)
            if table is None:
                return JSONResponse(status_code=404, content={
                    'error': {'code': 'TABLE_NOT_FOUND', 'message': 'Table not in the current inventory.'}})
            measured = collect_table_storage(target, inventory['size_bytes'], [table])
            final = target.lstat()
            identity = lambda item: (item.st_dev, item.st_ino, item.st_ctime_ns,
                                     item.st_size, item.st_mtime_ns)
            if (not stat.S_ISREG(initial.st_mode) or not stat.S_ISREG(final.st_mode)
                    or identity(initial) != identity(final)):
                raise InventoryError('CHANGED_DURING_READ', 'Database changed during inspection.')
        except OSError:
            return JSONResponse(status_code=422, content={
                'error': {'code': 'CHANGED_DURING_READ', 'message': 'Database changed during inspection.'}})
        except InventoryError as exc:
            return JSONResponse(status_code=422, content={'error': {
                'code': exc.code, 'message': exc.message}})
        metric = measured['tables'].get(name, {'status': 'unavailable',
                                                'reason': measured.get('reason', 'btree_not_measurable')})
        return JSONResponse({'contract': 'dbvora.local-table-storage.v1',
                             'table': name, 'scope': measured['scope'], 'metric': metric})

    @app.get('/api/observations')
    async def observations(request: Request):
        """Optional read-only local observation ledger; never accepts file paths."""
        if observation_ledger_path is None:
            return JSONResponse(status_code=404, content={
                'error': {'code': 'OBSERVATIONS_DISABLED', 'message': 'Local observation ledger is not configured.'}})
        database_ids = request.query_params.getlist('database')
        if (set(request.query_params.keys()) != {'database'}
                or len(database_ids) != 1 or database_ids[0] not in by_db_id):
            return JSONResponse(status_code=422, content={
                'error': {'code': 'INVALID_DATABASE', 'message': 'Select a configured database.'}})
        try:
            rows = read_observations(observation_ledger_path, db_id=database_ids[0])
        except (ObservationError, OSError, ValueError):
            return JSONResponse(status_code=422, content={
                'error': {'code': 'OBSERVATION_INTEGRITY', 'message': 'Local observation ledger is unavailable or invalid.'}})
        return JSONResponse({'contract': 'dbvora.local-observation.v1',
                             'database': database_ids[0],
                             'scope': 'sqlite_main_file_excluding_wal_shm',
                             'records': rows})

    @app.get('/health')
    async def health():
        return JSONResponse({'ok': True, 'mode': 'local-read-only'})

    return app

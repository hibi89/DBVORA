"""Export an entirely offline, read-only SQLite *schema* map in one HTML file.

This is a portable UI preview, never a SQLite backup or a trusted signed report.
No table rows, paths, external URLs or customer DB files are included. Use only
explicitly authorized synthetic databases until customer-readiness review.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from dbvora.errors import InventoryError
from dbvora.inventory import inspect_sqlite

_MAX_HTML_BYTES = 12 * 1024 * 1024
_WEB = Path(__file__).resolve().parent / 'web'
_STYLE_LINK = '<link rel="stylesheet" href="/assets/style.css">'
_SCRIPT_LINK = '<script src="/assets/app.js" defer></script>'
_CSP = ('default-src \'none\'; script-src \'unsafe-inline\'; '
        'style-src \'unsafe-inline\'; connect-src \'none\'; '
        'img-src \'none\'; font-src \'none\'; object-src \'none\'; '
        'base-uri \'none\'; form-action \'none\'; frame-ancestors \'none\'')


class HtmlExportError(Exception):
    """Machine-readable public error code, never the private source path."""


def _folder(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        raise HtmlExportError('INVALID_OUTPUT')
    try:
        if any(x.is_symlink() for x in (p, *p.parents)):
            raise HtmlExportError('INVALID_OUTPUT')
        if not stat.S_ISDIR(p.stat().st_mode):
            raise HtmlExportError('INVALID_OUTPUT')
    except OSError:
        raise HtmlExportError('INVALID_OUTPUT') from None
    return p


def render_html(schema: dict, *, web: Path = _WEB) -> bytes:
    """Never interpolate untrusted identifiers into HTML/script source.

    The entire metadata object is encoded as base64 and parsed at runtime,
    and app.js uses DOM textContent instead of innerHTML. A strict CSP blocks
    network activity from this file; the viewer needs neither HTTP nor pip.
    """
    try:
        document = (web / 'index.html').read_text(encoding='utf-8')
        stylesheet = (web / 'style.css').read_text(encoding='utf-8')
        script = (web / 'app.js').read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        raise HtmlExportError('MISSING_WEB_ASSET') from None
    if (document.count(_STYLE_LINK) != 1 or document.count(_SCRIPT_LINK) != 1
            or document.count('<meta charset="utf-8">') != 1
            or document.count('</body>') != 1
            or re.search(r'</\s*style\b', stylesheet, re.IGNORECASE)
            or re.search(r'</\s*script\b', script, re.IGNORECASE)):
        raise HtmlExportError('UNSAFE_WEB_ASSET')
    if not isinstance(schema, dict) or schema.get('engine') != 'sqlite':
        raise HtmlExportError('INVALID_SCHEMA')
    try:
        payload = json.dumps(schema, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        encoded = base64.b64encode(payload).decode('ascii')
    except (ValueError, TypeError, UnicodeError):
        raise HtmlExportError('INVALID_SCHEMA') from None
    # The data is a Base64 literal, not script or HTML. This avoids even a
    # malicious identifier containing a closing </script> tag crossing contexts.
    bootstrap = (
        '<script>\n'
        '"use strict";\n'
        f'const localSchemaBase64 = "{encoded}";\n'
        'const binary = atob(localSchemaBase64);\n'
        'const bytes = Uint8Array.from(binary, ch => ch.charCodeAt(0));\n'
        'const localSchema = JSON.parse(new TextDecoder().decode(bytes));\n'
        'window.fetch = async () => ({ok: true, json: async () => localSchema});\n'
        '</script>\n'
    )
    document = document.replace(_STYLE_LINK, '<style>\n' + stylesheet + '\n</style>')
    document = document.replace(_SCRIPT_LINK, '')
    # file: URLs do not supply server CSP headers; a meta CSP blocks network
    # while allowing the known local viewer inline JS/CSS.
    document = document.replace('<meta charset="utf-8">',
        '<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="' + _CSP + '">', 1)
    if '</body>' not in document:
        raise HtmlExportError('UNSAFE_WEB_ASSET')
    document = document.replace('</body>', bootstrap + '<script>\n' + script + '\n</script>\n</body>', 1)
    content = document.encode('utf-8')
    if len(content) > _MAX_HTML_BYTES:
        raise HtmlExportError('REPORT_TOO_LARGE')
    return content


def export(db_path: str | Path, output_dir: str | Path) -> dict:
    """New filename, never overwrite. A report is NOT a backup.

    Output is public metadata when shared; generated HTML may reveal schema
    names. Do not create reports containing unapproved schema information.
    """
    folder = _folder(output_dir)
    try:
        schema = inspect_sqlite(db_path)
    except InventoryError as exc:
        raise HtmlExportError(exc.code) from None
    content = render_html(schema)
    name = 'dbvora-map-' + uuid.uuid4().hex + '.html'
    result = folder / name
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
    fd = None
    try:
        fd = os.open(result, flags, 0o600)
        with os.fdopen(fd, 'wb') as out:
            fd = None
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
    except FileExistsError:
        raise HtmlExportError('ALREADY_EXISTS') from None
    except OSError:
        # Only the new name from our own exclusive creation may be unlinked.
        if fd is None and result.is_file() and not result.is_symlink():
            result.unlink(missing_ok=True)
        raise HtmlExportError('WRITE_FAILED') from None
    finally:
        if fd is not None:
            os.close(fd)
    return {'status': 'CREATED_OFFLINE_SCHEMA_HTML', 'filename': name,
            'size_bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
            'contains_table_rows': False, 'ready_for_customer_data': False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Offline metadata-only DBVORA HTML preview')
    parser.add_argument('--db', required=True, help='Explicit absolute SQLite path (not uploaded)')
    parser.add_argument('--out', required=True, help='Existing absolute local output directory')
    args = parser.parse_args(argv)
    try:
        report = export(args.db, args.out)
    except HtmlExportError as exc:
        report = {'status': 'FAIL_CLOSED', 'error_code': str(exc),
                  'ready_for_customer_data': False}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report['status'] == 'CREATED_OFFLINE_SCHEMA_HTML' else 1


if __name__ == '__main__':
    raise SystemExit(main())

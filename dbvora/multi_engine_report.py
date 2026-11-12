"""Zero-network, metadata-only mixed SQLite/PostgreSQL offline observatory.

This module does not establish connections or read data rows. It accepts only
explicitly supplied, already inspected catalog dictionaries; it strips source
paths and arbitrary keys. Cross-engine relationships are never inferred.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dbvora.archive.safe_zip import ArchiveError, _directory, _publish_new, _staging_file

MAX_DATABASES = 8
MAX_TABLES = 2000
MAX_COLUMNS = 500
MAX_INDEXES = 1000
MAX_RELATIONSHIPS = 4000
MAX_REPORT_BYTES = 5 * 1024 * 1024


class ReportError(ValueError):
    """Path- and data-free error code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str):
    raise ReportError(code)


def _name(value: Any) -> str:
    if type(value) is not str or not 1 <= len(value) <= 256 or '\x00' in value:
        _fail('INVALID_METADATA')
    return value


def _columns(columns: Any) -> list[dict]:
    if type(columns) is not list or len(columns) > MAX_COLUMNS:
        _fail('INVALID_COLUMNS')
    found = set()
    result = []
    for col in columns:
        if type(col) is not dict:
            _fail('INVALID_COLUMNS')
        name = _name(col.get('name'))
        if name in found:
            _fail('DUPLICATE_COLUMN')
        found.add(name)
        result.append({'name': name, 'type': _name(col.get('type') or 'unknown'),
                       'nullable': col.get('nullable_declared') is True,
                       'primary_key': bool(col.get('pk_position'))})
    return result


def _indexes(indexes: Any) -> list[dict]:
    if type(indexes) is not list or len(indexes) > MAX_INDEXES:
        _fail('INVALID_INDEXES')
    result = []
    for idx in indexes:
        if type(idx) is not dict or type(idx.get('key_columns')) is not list:
            _fail('INVALID_INDEXES')
        if len(idx['key_columns']) > MAX_COLUMNS:
            _fail('INVALID_INDEXES')
        result.append({'name': _name(idx.get('name')),
                       'columns': [_name(x) if x is not None else None for x in idx['key_columns']],
                       'unique': idx.get('unique') is True,
                       'partial': idx.get('partial') is True})
    return result


def _pg_statistics(value: Any) -> dict | None:
    """Keep only catalog-derived statistics with explicit measured/estimate labels."""
    if value is None:
        return None
    if type(value) is not dict or value.get('status') not in ('observed', 'unavailable'):
        _fail('INVALID_PG_STATISTICS')
    if value['status'] == 'unavailable':
        if (set(value) != {'status', 'reason'} or value['reason'] not in
                ('pg_statistics_unavailable', 'relation_not_in_statistics_view')):
            _fail('INVALID_PG_STATISTICS')
        return {'status': 'unavailable', 'reason': value['reason']}
    fields = {'status', 'estimated_live_rows', 'estimated_dead_rows',
              'heap_bytes', 'index_bytes', 'row_count_provenance', 'storage_provenance'}
    if set(value) != fields or value['row_count_provenance'] != 'pg_stat_user_tables_estimate_not_exact' or value['storage_provenance'] != 'pg_relation_size_and_pg_indexes_size':
        _fail('INVALID_PG_STATISTICS')
    for name in ('estimated_live_rows', 'estimated_dead_rows', 'heap_bytes', 'index_bytes'):
        if type(value[name]) is not int or not 0 <= value[name] <= 2**63 - 1:
            _fail('INVALID_PG_STATISTICS')
    return dict(value)


def _relationship(src: dict, fk: dict, *, engine: str, table_keys: set[str]) -> dict | None:
    if type(fk) is not dict:
        _fail('INVALID_RELATIONSHIP')
    if engine == 'sqlite':
        target = _name(fk.get('to_table'))
        source = _name(src['name'])
        source_cols = fk.get('from_columns')
        target_cols = fk.get('to_columns')
        target_key = target
        target_schema = None
    else:
        if fk.get('target_in_inventory') is not True:
            return None  # unresolved edges must never be presented as verified
        target = _name(fk.get('to_table'))
        target_schema = _name(fk.get('to_schema'))
        target_key = target_schema + '.' + target
        source = _name(src['schema']) + '.' + _name(src['name'])
        source_cols = fk.get('from_columns')
        target_cols = fk.get('to_columns')
    if target_key not in table_keys:
        return None
    if type(source_cols) is not list or not source_cols or len(source_cols) > MAX_COLUMNS:
        _fail('INVALID_RELATIONSHIP')
    if type(target_cols) is not list or len(target_cols) > MAX_COLUMNS:
        _fail('INVALID_RELATIONSHIP')
    return {'from': source, 'to': target_key,
            'from_columns': [_name(v) for v in source_cols],
            'to_columns': [_name(v) for v in target_cols],
            'evidence': 'declared_foreign_key', 'verified_across_databases': False}


def assemble_workspace(catalogs: list[dict]) -> dict:
    """Normalize prior SQLite/PG metadata. No DB paths, DSNs or rows are copied."""
    if type(catalogs) not in (list, tuple) or not 1 <= len(catalogs) <= MAX_DATABASES:
        _fail('INVALID_DATABASE_COUNT')
    databases = []
    total_tables = 0
    for n, inv in enumerate(catalogs, 1):
        if type(inv) is not dict or inv.get('engine') not in ('sqlite', 'postgresql'):
            _fail('UNSUPPORTED_ENGINE')
        engine = inv['engine']
        tables = inv.get('tables')
        if type(tables) is not list or total_tables + len(tables) > MAX_TABLES:
            _fail('TABLE_LIMIT')
        total_tables += len(tables)
        keys = set()
        for table in tables:
            if type(table) is not dict:
                _fail('INVALID_METADATA')
            schema = _name(table.get('schema')) if engine == 'postgresql' else None
            name = _name(table.get('name'))
            key = (schema + '.' if schema is not None else '') + name
            if key in keys:
                _fail('DUPLICATE_TABLE')
            keys.add(key)
        output_tables = []
        relationships = []
        for table in tables:
            schema = _name(table['schema']) if engine == 'postgresql' else None
            name = _name(table['name'])
            key = (schema + '.' if schema is not None else '') + name
            size = table.get('size_bytes') if engine == 'postgresql' else None
            if size is not None and (type(size) is not int or size < 0):
                _fail('INVALID_SIZE')
            columns = _columns(table.get('columns'))
            if engine == 'postgresql':
                declared_pk = table.get('primary_key_columns', [])
                if type(declared_pk) is not list or len(declared_pk) > MAX_COLUMNS:
                    _fail('INVALID_PRIMARY_KEY')
                known = {col['name'] for col in columns}
                if any(type(x) is not str or x not in known for x in declared_pk):
                    _fail('INVALID_PRIMARY_KEY')
                for col in columns:
                    col['primary_key'] = col['name'] in declared_pk
            indexes = _indexes(table.get('indexes'))
            fks = table.get('foreign_keys')
            if type(fks) is not list or len(fks) > MAX_RELATIONSHIPS:
                _fail('INVALID_RELATIONSHIP')
            normalized = {'key': key, 'name': name, 'schema': schema,
                          'size_bytes': size, 'size_kind': 'pg_total_relation_size' if size is not None else 'unavailable',
                          'columns': columns, 'indexes': indexes}
            if engine == 'postgresql':
                normalized['statistics'] = _pg_statistics(table.get('statistics'))
            output_tables.append(normalized)
            for fk in fks:
                edge = _relationship(table, fk, engine=engine, table_keys=keys)
                if edge is not None:
                    relationships.append(edge)
            if len(relationships) > MAX_RELATIONSHIPS:
                _fail('RELATIONSHIP_LIMIT')
        databases.append({'id': n, 'label': 'Database ' + str(n), 'engine': engine,
                          'table_count': len(output_tables), 'tables': output_tables,
                          'relationships': relationships})
    return {'contract_version': 'dbvora.multi_engine_offline.v1',
            'scope': 'explicit_metadata_only_no_row_data',
            'database_count': len(databases), 'table_count': total_tables,
            'cross_database_edges_verified': 0,
            'cross_database_relationships': 'not_inferred',
            'cpu_usage': 'unavailable', 'ram_usage': 'unavailable',
            'databases': databases, 'ready_for_customer_data': False}


_HTML = r'''<!doctype html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<title>DBVORA — Mixed Database Observatory</title>
<style>
:root{color-scheme:dark;font:14px system-ui,sans-serif;background:#0b1220;color:#eaf0fc}*{box-sizing:border-box}body{margin:0 auto;max-width:1400px;padding:32px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #344558;padding-bottom:20px}h1{font-size:30px;margin:5px 0}h2{font-size:19px}.sub{color:#a0b4c8}.tag{color:#83ead3;font-weight:650;font-size:12px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:26px 0}.kpi{background:#152338;padding:18px;border-radius:12px;border:1px solid #344558}.kpi strong{display:block;font-size:27px}.layout{display:grid;grid-template-columns:minmax(300px,1fr) minmax(350px,1fr);gap:20px}.panel{background:#111d30;border:1px solid #344558;border-radius:14px;padding:20px}.db{padding:12px 0;border-top:1px solid #304052}.dbtitle{margin:0 0 12px;font-weight:700;color:#9cebd9}.nodes{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}button{font:inherit;color:#eaf0fc;text-align:left;background:#21344a;border:1px solid #3f5974;border-radius:10px;padding:12px;overflow-wrap:anywhere;cursor:pointer}button[aria-pressed=true],button:focus-visible{border:2px solid #8bd8c5;outline:none}.table-key{display:block;font-weight:650}.node-sub{color:#a9b9c9;font-size:12px}input{width:100%;padding:12px;background:#0b1827;color:inherit;border:1px solid #466079;border-radius:9px;margin-bottom:15px}ul{list-style:none;padding:0}li{border-bottom:1px solid #344558;padding:9px 0;overflow-wrap:anywhere}.pill{border:1px solid #486479;border-radius:8px;padding:3px 6px;color:#9cebd9;font-size:11px}.muted{color:#a0b4c8}.hidden{display:none!important}footer{margin-top:30px;font-size:12px;color:#97a9bd}@media(max-width:850px){body{padding:18px}.layout{grid-template-columns:1fr}}
</style></head><body>
<header><div><div class="tag">DBVORA · OFFLINE · READ ONLY</div><h1>Database Observatory</h1><div class="sub">SQLite + PostgreSQL 메타데이터 구조 탐색</div></div><div class="tag">LOCAL FILE · NO NETWORK</div></header>
<section class="kpis"><div class="kpi"><span class="sub">DATABASES</span><strong id="db-count">—</strong></div><div class="kpi"><span class="sub">TABLES</span><strong id="table-count">—</strong></div><div class="kpi"><span class="sub">RELATIONSHIPS</span><strong id="edge-count">—</strong></div><div class="kpi"><span class="sub">CPU / RAM</span><strong>N/A</strong><small class="muted">DB별 측정 불가</small></div></section>
<div class="layout"><section class="panel"><h2>Structure map</h2><label class="sub" for="search">테이블 검색</label><input id="search" type="search" autocomplete="off" placeholder="테이블 또는 스키마 검색"><div id="databases" aria-label="데이터베이스 노드"></div></section><section class="panel"><h2 id="selection">Select a table</h2><div class="sub" id="meta">노드를 클릭하면 컬럼·인덱스를 확인할 수 있습니다.</div><h2>Estimated PostgreSQL statistics</h2><div class="sub" id="pg-stats">Optional statistics not collected</div><h2>Columns</h2><ul id="columns"></ul><h2>Indexes</h2><ul id="indexes"></ul><h2>Declared relationships</h2><ul id="relations"></ul></section></div>
<footer>데이터 행·접속 정보·SQL 원문을 포함하지 않습니다. 선언된 DB 내부 관계만 표시하며 DB 사이 관계는 추론하지 않습니다. 백업 및 고객 서비스 출시 검증과는 별개입니다.</footer>
<script type="application/json" id="catalog">__DBVORA_CATALOG_JSON__</script>
<script>
'use strict';
const model=JSON.parse(document.getElementById('catalog').textContent);
const $=id=>document.getElementById(id);
const nodes=[];
function tag(name,text,cls){const elem=document.createElement(name);if(cls)elem.className=cls;if(text!==undefined)elem.textContent=String(text);return elem;}
function clear(elem){elem.replaceChildren();}
function rows(id,items,fn){const area=$(id);clear(area);if(!items.length)area.append(tag('li','—','muted'));for(const item of items)area.append(tag('li',fn(item)));}
function choose(db,table,button){for(const item of nodes)item.button.setAttribute('aria-pressed',String(item.button===button));
$('selection').textContent=db.label+' / '+table.key;
$('meta').textContent=db.engine.toUpperCase()+' · '+table.columns.length+' columns · '+table.indexes.length+' indexes · size '+(table.size_bytes===null?'unavailable':table.size_bytes.toLocaleString('en-US')+' bytes');
const stats=table.statistics;
$('pg-stats').textContent=stats&&stats.status==='observed'
  ? 'Estimated live rows ≈'+stats.estimated_live_rows.toLocaleString('en-US')+
    ' · dead rows ≈'+stats.estimated_dead_rows.toLocaleString('en-US')+
    ' · measured heap '+stats.heap_bytes.toLocaleString('en-US')+' bytes'+
    ' · measured indexes '+stats.index_bytes.toLocaleString('en-US')+' bytes'
  : (db.engine==='postgresql'?'Not collected or unavailable (no fabricated zero)':'PostgreSQL only');
rows('columns',table.columns,c=>c.name+' · '+c.type+(c.primary_key?' · PK':'')+(c.nullable?' · nullable':''));
rows('indexes',table.indexes,i=>i.name+' ('+i.columns.map(c=>c===null?'expression':c).join(', ')+')'+(i.unique?' · unique':''));
rows('relations',db.relationships.filter(r=>r.from===table.key||r.to===table.key),r=>r.from+' → '+r.to+' ['+r.evidence+']');}
$('db-count').textContent=model.database_count;$('table-count').textContent=model.table_count;
$('edge-count').textContent=model.databases.reduce((n,db)=>n+db.relationships.length,0);
for(const db of model.databases){const container=tag('div',undefined,'db'),title=tag('p',db.label+' · '+db.engine.toUpperCase()+' · '+db.table_count+' tables','dbtitle');container.append(title);const grid=tag('div',undefined,'nodes');for(const table of db.tables){const button=tag('button',undefined,'node');button.type='button';button.setAttribute('aria-pressed','false');button.append(tag('span',table.key,'table-key'),tag('small',table.columns.length+' columns','node-sub'));button.addEventListener('click',()=>choose(db,table,button));grid.append(button);nodes.push({db,table,button});}container.append(grid);$('databases').append(container);}
$('search').addEventListener('input',event=>{const query=event.target.value.toLocaleLowerCase();for(const item of nodes)item.button.classList.toggle('hidden',!item.table.key.toLocaleLowerCase().includes(query));});
</script></body></html>'''


def render_report(workspace: dict) -> str:
    if type(workspace) is not dict or workspace.get('contract_version') != 'dbvora.multi_engine_offline.v1' or workspace.get('ready_for_customer_data') is not False:
        _fail('INVALID_WORKSPACE')
    # Disallow supplementary arbitrary fields from a caller: only the schema
    # normalizer controls what can become HTML content.
    clean = assemble_workspace([{
        'engine': db['engine'],
        'tables': [{
            'schema': t.get('schema'), 'name': t['name'], 'size_bytes': t['size_bytes'],
            'columns': [{'name': c['name'], 'type': c['type'], 'nullable_declared': c['nullable'],
                         'pk_position': 1 if c['primary_key'] else 0} for c in t['columns']],
            'indexes': [{'name': i['name'], 'key_columns': i['columns'],
                         'unique': i['unique'], 'partial': i['partial']} for i in t['indexes']],
            'primary_key_columns': [c['name'] for c in t['columns'] if c['primary_key']],
            'statistics': t.get('statistics'),
            'foreign_keys': [],  # relationships explicitly revalidated below
        } for t in db['tables']]
    } for db in workspace['databases']])
    # Add only verified, same-DB declared links. A forged cross DB link is dropped.
    for dst, original in zip(clean['databases'], workspace['databases']):
        keys = {t['key'] for t in dst['tables']}
        clean_edges = []
        for edge in original.get('relationships', []):
            if (type(edge) is dict and edge.get('evidence') == 'declared_foreign_key'
                    and edge.get('verified_across_databases') is False
                    and edge.get('from') in keys and edge.get('to') in keys):
                clean_edges.append({'from': edge['from'], 'to': edge['to'],
                                    'evidence': 'declared_foreign_key'})
        dst['relationships'] = clean_edges[:MAX_RELATIONSHIPS]
    payload = json.dumps(clean, ensure_ascii=True, separators=(',', ':'))
    # Prevent any metadata identifier from escaping the script data element.
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = _HTML.replace('__DBVORA_CATALOG_JSON__', payload)
    if len(page.encode('utf-8')) > MAX_REPORT_BYTES:
        _fail('REPORT_TOO_LARGE')
    return page


def export_report(catalogs: list[dict], output_directory: str | Path) -> dict:
    """Publish one immutable, separately named HTML. Never overwrite files."""
    page = render_report(assemble_workspace(catalogs))
    try:
        output = _directory(output_directory)
        stage = _staging_file(output)
        try:
            with stage.open('wb') as stream:
                encoded = page.encode('utf-8')
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            result = _publish_new(stage, output, '.html')
            return {'status': 'OFFLINE_METADATA_REPORT_CREATED', 'filename': result.name,
                    'bytes': len(encoded), 'ready_for_customer_data': False,
                    'cross_database_edges_verified': 0}
        finally:
            stage.unlink(missing_ok=True)
    except ArchiveError as exc:
        raise ReportError(exc.code) from None
    except (OSError, ValueError, TypeError):
        raise ReportError('REPORT_WRITE_FAILED') from None

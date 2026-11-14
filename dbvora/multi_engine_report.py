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
from dbvora.optimization_review import review_statistics

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


def _table_identity(engine: str, schema: str | None, name: str) -> str:
    return json.dumps([engine, schema, name], ensure_ascii=False, separators=(',', ':'))


def _relationship(src: dict, fk: dict, *, engine: str,
                  table_index: dict[tuple[str | None, str], dict]) -> dict | None:
    if type(fk) is not dict:
        _fail('INVALID_RELATIONSHIP')
    source_schema = None if engine == 'sqlite' else _name(src['schema'])
    source_name = _name(src['name'])
    source_entry = table_index.get((source_schema, source_name))
    if source_entry is None:
        _fail('INVALID_RELATIONSHIP')
    if engine == 'sqlite':
        target = _name(fk.get('to_table'))
        target_schema = None
    else:
        if fk.get('target_in_inventory') is not True:
            return None  # unresolved edges must never be presented as verified
        target = _name(fk.get('to_table'))
        target_schema = _name(fk.get('to_schema'))
    target_entry = table_index.get((target_schema, target))
    if target_entry is None:
        return None
    source_cols = fk.get('from_columns')
    target_cols = fk.get('to_columns')
    if type(source_cols) is not list or not source_cols or len(source_cols) > MAX_COLUMNS:
        _fail('INVALID_RELATIONSHIP')
    if type(target_cols) is not list or len(target_cols) > MAX_COLUMNS:
        _fail('INVALID_RELATIONSHIP')
    return {'from': source_entry['key'], 'to': target_entry['key'],
            'from_identity': source_entry['identity'], 'to_identity': target_entry['identity'],
            'from_columns': [_name(v) for v in source_cols],
            'to_columns': [_name(v) for v in target_cols],
            'evidence': 'declared_foreign_key', 'verified_across_databases': False}


_LINK_FIELDS = frozenset({
    'from_db', 'from_schema', 'from_table', 'from_column',
    'to_db', 'to_schema', 'to_table', 'to_column',
})
MAX_DECLARED_LINKS = 64


def _declared_links(databases: list[dict], declarations: list[dict] | None) -> list[dict]:
    if declarations is None:
        declarations = []
    if type(declarations) is not list or len(declarations) > MAX_DECLARED_LINKS:
        _fail('INVALID_LINK_COUNT')
    result = []
    fingerprints = set()
    for entry in declarations:
        if type(entry) is not dict or set(entry) != _LINK_FIELDS:
            _fail('INVALID_LINK')
        source_db, target_db = entry['from_db'], entry['to_db']
        if (type(source_db) is not int or type(target_db) is not int
                or not 1 <= source_db <= len(databases)
                or not 1 <= target_db <= len(databases)
                or source_db == target_db):
            _fail('INVALID_LINK_ENDPOINT')

        def endpoint(db_id: int, schema_value: Any, table_value: Any,
                     column_value: Any) -> tuple[dict, str, str | None, str]:
            database = databases[db_id - 1]
            engine = database['engine']
            table_name = _name(table_value)
            column_name = _name(column_value)
            if engine == 'sqlite':
                if schema_value is not None:
                    _fail('INVALID_LINK_ENDPOINT')
                schema_name = None
            else:
                schema_name = _name(schema_value)
            matches = [table for table in database['tables']
                       if table['name'] == table_name and table['schema'] == schema_name]
            if len(matches) != 1 or not any(
                    column['name'] == column_name for column in matches[0]['columns']):
                _fail('UNKNOWN_LINK_COLUMN')
            table = matches[0]
            return table, table_name, schema_name, column_name

        source_table, source_name, source_schema, source_column = endpoint(
            source_db, entry['from_schema'], entry['from_table'], entry['from_column'])
        target_table, target_name, target_schema, target_column = endpoint(
            target_db, entry['to_schema'], entry['to_table'], entry['to_column'])
        fingerprint = (source_db, source_schema, source_name, source_column,
                      target_db, target_schema, target_name, target_column)
        if fingerprint in fingerprints:
            _fail('DUPLICATE_LINK')
        fingerprints.add(fingerprint)
        source = databases[source_db - 1]
        target = databases[target_db - 1]
        result.append({
            'from_db': source_db, 'from_db_id': source['id'], 'from_db_label': source['label'],
            'from_schema': source_schema, 'from_table': source_name,
            'from_table_key': source_table['key'], 'from_table_identity': source_table['identity'],
            'from_column': source_column,
            'to_db': target_db, 'to_db_id': target['id'], 'to_db_label': target['label'],
            'to_schema': target_schema, 'to_table': target_name,
            'to_table_key': target_table['key'], 'to_table_identity': target_table['identity'],
            'to_column': target_column,
            'evidence': 'user_declared_unverified', 'verified': False,
        })
    return result


def assemble_workspace(catalogs: list[dict], *,
                       declared_links: list[dict] | None = None) -> dict:
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
        table_index: dict[tuple[str | None, str], dict] = {}
        preferred_counts: dict[str, int] = {}
        for table in tables:
            if type(table) is not dict:
                _fail('INVALID_METADATA')
            schema = _name(table.get('schema')) if engine == 'postgresql' else None
            name = _name(table.get('name'))
            endpoint_key = (schema, name)
            if endpoint_key in table_index:
                _fail('DUPLICATE_TABLE')
            key = (schema + '.' if schema is not None else '') + name
            identity = _table_identity(engine, schema, name)
            table_index[endpoint_key] = {'key': key, 'identity': identity}
            preferred_counts[key] = preferred_counts.get(key, 0) + 1
        for (schema, name), info in table_index.items():
            if preferred_counts[info['key']] > 1:
                # Dotted schema/table names can otherwise produce an ambiguous
                # display key even though their catalog identities are distinct.
                info['key'] = json.dumps([engine, schema, name], ensure_ascii=False,
                                         separators=(',', ':'))

        output_tables = []
        relationships = []
        for table in tables:
            schema = _name(table['schema']) if engine == 'postgresql' else None
            name = _name(table['name'])
            endpoint_info = table_index[(schema, name)]
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
            normalized = {'identity': endpoint_info['identity'], 'key': endpoint_info['key'],
                          'name': name, 'schema': schema,
                          'size_bytes': size, 'size_kind': 'pg_total_relation_size' if size is not None else 'unavailable',
                          'columns': columns, 'indexes': indexes}
            if engine == 'postgresql':
                normalized['statistics'] = _pg_statistics(table.get('statistics'))
                normalized['optimization_review'] = review_statistics(normalized['statistics'])
            output_tables.append(normalized)
            for fk in fks:
                edge = _relationship(table, fk, engine=engine, table_index=table_index)
                if edge is not None:
                    relationships.append(edge)
            if len(relationships) > MAX_RELATIONSHIPS:
                _fail('RELATIONSHIP_LIMIT')
        databases.append({'id': n, 'label': 'Database ' + str(n), 'engine': engine,
                          'table_count': len(output_tables), 'tables': output_tables,
                          'relationships': relationships})
    cross_links = _declared_links(databases, declared_links)
    return {'contract_version': 'dbvora.multi_engine_offline.v1',
            'scope': 'explicit_metadata_only_no_row_data',
            'database_count': len(databases), 'table_count': total_tables,
            'cross_database_edges_verified': 0,
            'cross_database_relationships': 'not_inferred',
            'declared_cross_database_count': len(cross_links),
            'declared_cross_database_links': cross_links,
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
<section class="kpis"><div class="kpi"><span class="sub">DATABASES</span><strong id="db-count">—</strong></div><div class="kpi"><span class="sub">TABLES</span><strong id="table-count">—</strong></div><div class="kpi"><span class="sub">DECLARED RELATIONSHIPS</span><strong id="edge-count">—</strong></div><div class="kpi"><span class="sub">CPU / RAM</span><strong>N/A</strong><small class="muted">DB별 측정 불가</small></div></section>
<div class="layout"><section class="panel"><h2>Structure map</h2><label class="sub" for="search">테이블 검색</label><input id="search" type="search" autocomplete="off" placeholder="테이블 또는 스키마 검색"><div id="databases" aria-label="데이터베이스 노드"></div></section><section class="panel"><h2 id="selection">Select a table</h2><div class="sub" id="meta">노드를 클릭하면 컬럼·인덱스를 확인할 수 있습니다.</div><h2>Estimated PostgreSQL statistics</h2><div class="sub" id="pg-stats">Optional statistics not collected</div><h2>Optimization review · manual only</h2><div class="sub" id="pg-review">No actions taken</div><h2>Columns</h2><ul id="columns"></ul><h2>Indexes</h2><ul id="indexes"></ul><h2>Database-local relationships</h2><ul id="relations"></ul></section></div>
<section class="panel" style="margin-top:16px"><h2>Declared cross-database links <small>(user-declared · unverified)</small></h2><ul id="cross-database-links"></ul></section><footer>데이터 행·접속 정보·SQL 원문을 포함하지 않습니다. DB 사이 링크는 사용자가 명시한 구조 선언이며 검증된 FK가 아닙니다. 선언되지 않은 관계는 추론하지 않습니다. 백업 및 고객 서비스 출시 검증과는 별개입니다.</footer>
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
const review=table.optimization_review;
$('pg-review').textContent=review&&review.rules.length
  ? review.rules.map(x=>x.label).join(' · ')+' · estimates are not confirmed waste'
  : 'No evidence-based action; no automatic SQL or storage savings claim';
rows('columns',table.columns,c=>c.name+' · '+c.type+(c.primary_key?' · PK':'')+(c.nullable?' · nullable':''));
rows('indexes',table.indexes,i=>i.name+' ('+i.columns.map(c=>c===null?'expression':c).join(', ')+')'+(i.unique?' · unique':''));
rows('relations',db.relationships.filter(r=>r.from_identity===table.identity||r.to_identity===table.identity),r=>r.from+' → '+r.to+' ['+r.evidence+']');}
$('db-count').textContent=model.database_count;$('table-count').textContent=model.table_count;
$('edge-count').textContent=model.databases.reduce((n,db)=>n+db.relationships.length,0)+(model.declared_cross_database_count||0);
for(const db of model.databases){const container=tag('div',undefined,'db'),title=tag('p',db.label+' · '+db.engine.toUpperCase()+' · '+db.table_count+' tables','dbtitle');container.append(title);const grid=tag('div',undefined,'nodes');for(const table of db.tables){const button=tag('button',undefined,'node');button.type='button';button.setAttribute('aria-pressed','false');button.setAttribute('data-database-id',String(db.id));button.setAttribute('data-table-identity',table.identity);button.append(tag('span',table.key,'table-key'),tag('small',table.columns.length+' columns','node-sub'));button.addEventListener('click',()=>choose(db,table,button));grid.append(button);nodes.push({db,table,button});}container.append(grid);$('databases').append(container);}
$('search').addEventListener('input',event=>{const query=event.target.value.toLocaleLowerCase();for(const item of nodes)item.button.classList.toggle('hidden',!(item.db.label+' '+item.table.key).toLocaleLowerCase().includes(query));});
const cross=$('cross-database-links'),links=model.declared_cross_database_links||[];
if(!links.length)cross.append(tag('li','No cross-database links declared. Relationships are never inferred.','muted'));
for(const link of links){const item=tag('li'),button=tag('button');button.type='button';button.setAttribute('aria-label','User-declared unverified cross-database link');
const fromName=(link.from_schema===null?'':link.from_schema+'.')+link.from_table;
const toName=(link.to_schema===null?'':link.to_schema+'.')+link.to_table;
button.append(tag('strong',link.from_db_label+' · '+fromName+'.'+link.from_column),tag('small','→ '+link.to_db_label+' · '+toName+'.'+link.to_column+' · user-declared / unverified','node-sub'));
button.addEventListener('click',()=>{const target=nodes.find(n=>n.db.id===link.to_db_id&&n.table.identity===link.to_table_identity);if(target){choose(target.db,target.table,target.button);target.button.focus();}});item.append(button);cross.append(item);}
</script></body></html>'''


def render_report(workspace: dict) -> str:
    if (type(workspace) is not dict
            or workspace.get('contract_version') != 'dbvora.multi_engine_offline.v1'
            or workspace.get('ready_for_customer_data') is not False
            or type(workspace.get('databases')) is not list):
        _fail('INVALID_WORKSPACE')
    # Rebuild normalized catalog values. Caller-supplied HTML and identifiers
    # never bypass the same validator used for connector output.
    catalogs = []
    for db in workspace['databases']:
        if type(db) is not dict or type(db.get('tables')) is not list:
            _fail('INVALID_WORKSPACE')
        catalogs.append({
            'engine': db.get('engine'),
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
        })
    raw_links = workspace.get('declared_cross_database_links', [])
    if type(raw_links) is not list:
        _fail('INVALID_LINK_COUNT')
    declarations = []
    for link in raw_links:
        if type(link) is not dict or not _LINK_FIELDS.issubset(link):
            _fail('INVALID_LINK')
        declarations.append({key: link.get(key) for key in _LINK_FIELDS})
    clean = assemble_workspace(catalogs, declared_links=declarations)
    # Revalidate database-local FK edges against a fully scoped table identity
    # and exact normalized columns before allowing them into the offline HTML.
    for dst, original in zip(clean['databases'], workspace['databases']):
        by_identity = {t['identity']: t for t in dst['tables']}
        edges = []
        for edge in original.get('relationships', []):
            if (type(edge) is not dict or edge.get('evidence') != 'declared_foreign_key'
                    or edge.get('verified_across_databases') is not False):
                continue
            source = by_identity.get(edge.get('from_identity'))
            target = by_identity.get(edge.get('to_identity'))
            if source is None or target is None:
                continue
            source_cols, target_cols = edge.get('from_columns'), edge.get('to_columns')
            if (type(source_cols) is not list or not source_cols
                    or type(target_cols) is not list or len(source_cols) != len(target_cols)
                    or any(type(c) is not str or c not in {x['name'] for x in source['columns']}
                           for c in source_cols)
                    or any(type(c) is not str or c not in {x['name'] for x in target['columns']}
                           for c in target_cols)):
                continue
            edges.append({
                'from': source['key'], 'to': target['key'],
                'from_identity': source['identity'], 'to_identity': target['identity'],
                'from_columns': list(source_cols), 'to_columns': list(target_cols),
                'evidence': 'declared_foreign_key', 'verified_across_databases': False,
            })
        dst['relationships'] = edges[:MAX_RELATIONSHIPS]
    payload = json.dumps(clean, ensure_ascii=True, separators=(',', ':'))
    # Prevent any metadata identifier from escaping the script data element.
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = _HTML.replace('__DBVORA_CATALOG_JSON__', payload)
    if len(page.encode('utf-8')) > MAX_REPORT_BYTES:
        _fail('REPORT_TOO_LARGE')
    return page


def export_report(catalogs: list[dict], output_directory: str | Path, *,
                  declared_links: list[dict] | None = None) -> dict:
    """Publish one immutable, separately named HTML. Never overwrite files."""
    workspace = assemble_workspace(catalogs, declared_links=declared_links)
    page = render_report(workspace)
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
                    'cross_database_edges_verified': 0,
                    'declared_cross_database_count': workspace['declared_cross_database_count']}
        finally:
            stage.unlink(missing_ok=True)
    except ArchiveError as exc:
        raise ReportError(exc.code) from None
    except (OSError, ValueError, TypeError):
        raise ReportError('REPORT_WRITE_FAILED') from None

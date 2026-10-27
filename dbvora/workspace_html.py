"""Zero-dependency, offline clickable multi-SQLite map. No paths or row contents."""
from __future__ import annotations

import argparse
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import uuid
from dbvora.errors import InventoryError
from dbvora.workspace import inspect_workspace

_PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<title>DBVORA Multi-DB Map</title><style>
:root{font-family:system-ui,sans-serif;background:#0c1523;color:#e7f0fa;color-scheme:dark}*{box-sizing:border-box}
body{margin:auto;padding:24px;max-width:1450px}h1{margin:0;font-size:26px}header{display:flex;justify-content:space-between;border-bottom:1px solid #304255;padding-bottom:15px}
small,.muted{color:#a1aec0}.dbs{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0}
.grid{display:grid;grid-template-columns:1.2fr 1fr;gap:16px}.panel{padding:16px;background:#101e2e;border:1px solid #304255;border-radius:11px;min-width:0}
button{font:inherit;cursor:pointer;color:inherit;border:1px solid #33465d;border-radius:9px;background:#16263a;text-align:left;padding:13px}
button[aria-pressed=true]{border-color:#45d2bb;background:#17384c}button strong{display:block;margin-bottom:7px;overflow-wrap:anywhere}
.tables{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:9px}svg{width:100%;max-width:100%;background:#0d1b2c;border-radius:8px;margin-top:12px}
#relationships{list-style:none;padding:0;font-size:13px;color:#bed0df;overflow-wrap:anywhere}#relationships li{padding:5px 0;border-bottom:1px solid #223649}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:13px}td,th{padding:7px;border-bottom:1px solid #283b50;text-align:left;overflow-wrap:anywhere}
.note{color:#9daebe;font-size:12px;margin-top:14px}@media(max-width:780px){body{padding:12px}.grid{grid-template-columns:1fr}header{display:block}}
</style></head><body><header><div><h1>DBVORA <small>Multi-DB Map</small></h1><p class="muted">Offline schema topology — select a database and table</p></div><strong id="summary"></strong></header>
<main><h2>Databases</h2><div class="dbs" id="databases"></div><div class="grid"><section class="panel"><h2>Tables &amp; declared FK</h2><div id="tables" class="tables"></div><svg id="graph" role="img" aria-label="Foreign key links"></svg><ul id="relationships"></ul></section>
<section class="panel"><h2>Table details</h2><div id="details" aria-live="polite">Select a table</div></section></div><p class="note">Main database file sizes only (WAL/SHM excluded). CPU/RAM and cross-database links are unverified. No customer paths or table row contents embedded.</p></main>
<script>"use strict";
const encodedWorkspace="__BASE64__";
const workspace=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(encodedWorkspace),c=>c.charCodeAt(0))));
const get=id=>document.getElementById(id),make=(tag,txt)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=String(txt);return e};
let activeDB=0;const size=n=>n<1024?n+' B':(n/1024).toFixed(1)+' KiB';
function details(index){const db=workspace.databases[activeDB],t=db.tables[index],pane=get('details');pane.replaceChildren();
 [...get('tables').children].forEach((node,i)=>node.setAttribute('aria-pressed',String(i===index)));
 if(!t){pane.append(make('p','No user tables'));return}pane.append(make('h3',t.name),make('p',t.columns.length+' columns · '+t.indexes.length+' indexes'));
 const grid=make('table'),head=make('tr');['Column','Type','Key'].forEach(x=>head.append(make('th',x)));grid.append(head);
 t.columns.forEach(c=>{const row=make('tr');[c.name,c.type||'—',c.pk_position?'PK '+c.pk_position:'—'].forEach(x=>row.append(make('td',x)));grid.append(row)});pane.append(grid);
 t.foreign_keys.forEach(f=>pane.append(make('p',f.from_columns.join(', ')+' → '+f.to_table+' ('+f.to_columns.join(', ')+')')));
 t.indexes.forEach(i=>pane.append(make('p','Index: '+i.name+(i.unique?' · unique':''))));}
function draw(db){const svg=get('graph');svg.replaceChildren();const names=db.tables.map(t=>t.name),ns='http://www.w3.org/2000/svg';
 const pos=i=>[10+(i%3)*215,10+Math.floor(i/3)*78];svg.setAttribute('viewBox','0 0 650 '+Math.max(80,Math.ceil(names.length/3)*78+20));
 function element(tag,attrs,text){const node=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>node.setAttribute(k,String(v)));if(text!==undefined)node.textContent=text;svg.append(node)}
 const edges=workspace.relationships.filter(e=>e.database_id===db.db_id);edges.filter(e=>e.target_in_inventory).forEach(e=>{const a=names.indexOf(e.from_table),b=names.indexOf(e.to_table);if(a<0||b<0)return;
 const [x,y]=pos(a),[xx,yy]=pos(b);element('line',{x1:x+100,y1:y+45,x2:xx+100,y2:yy+45,stroke:'#45d2bb','stroke-width':2})});
 names.forEach((n,i)=>{const [x,y]=pos(i);element('rect',{x,y,width:194,height:48,rx:8,fill:'#21455b',stroke:'#4f9b9e'});element('text',{x:x+10,y:y+27,fill:'#f0f5fa','font-size':12},n.length>25?n.slice(0,22)+'…':n)});
 const list=get('relationships');list.replaceChildren();if(!edges.length)list.append(make('li','No declared foreign keys'));
 edges.forEach(e=>list.append(make('li',e.from_table+'.'+e.from_columns.join(', ')+' → '+e.to_table+'.'+e.to_columns.join(', ')+' ('+(e.target_in_inventory?'declared FK':'target absent')+')')));}
function choose(index){activeDB=index;const db=workspace.databases[index],root=get('tables');root.replaceChildren();
 [...get('databases').children].forEach((node,i)=>node.setAttribute('aria-pressed',String(i===index)));
 db.tables.forEach((t,i)=>{const button=make('button');button.type='button';button.append(make('strong',t.name),make('span',t.columns.length+' columns · '+t.indexes.length+' indexes'));button.addEventListener('click',()=>details(i));root.append(button)});
 details(0);draw(db)}
get('summary').textContent=workspace.database_count+' databases · '+workspace.table_count+' tables · '+size(workspace.total_main_db_size_bytes);
workspace.databases.forEach((db,i)=>{const button=make('button');button.type='button';button.append(make('strong',db.label),make('span',db.tables.length+' tables · '+size(db.size_bytes)));button.addEventListener('click',()=>choose(i));get('databases').append(button)});choose(0);
</script></body></html>'''

class WorkspaceHtmlError(Exception):
    """Public stable error code, never a customer path or schema identifier."""


def _folder(destination: str | Path) -> Path:
    if not isinstance(destination, (str, Path)):
        raise WorkspaceHtmlError('INVALID_OUTPUT')
    p=Path(destination)
    if not p.is_absolute():
        raise WorkspaceHtmlError('INVALID_OUTPUT')
    try:
        if any(x.is_symlink() for x in (p,*p.parents)) or not stat.S_ISDIR(p.stat().st_mode):
            raise WorkspaceHtmlError('INVALID_OUTPUT')
    except OSError:
        raise WorkspaceHtmlError('INVALID_OUTPUT') from None
    return p


def render_workspace_html(workspace: dict) -> bytes:
    if not isinstance(workspace,dict) or workspace.get('contract_version')!='p0-03.workspace.v1' or not isinstance(workspace.get('databases'),list):
        raise WorkspaceHtmlError('INVALID_WORKSPACE')
    try:
        encoded=base64.b64encode(json.dumps(workspace,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')).decode('ascii')
    except (TypeError,ValueError,UnicodeError):
        raise WorkspaceHtmlError('INVALID_WORKSPACE') from None
    content=_PAGE.replace('__BASE64__',encoded).encode('utf-8')
    if len(content)>12*1024*1024:
        raise WorkspaceHtmlError('REPORT_TOO_LARGE')
    return content


def export_workspace(db_paths:list[str | Path],output_directory:str | Path)->dict:
    folder=_folder(output_directory)
    workspace=inspect_workspace(db_paths)
    content=render_workspace_html(workspace)
    name='dbvora-workspace-'+uuid.uuid4().hex+'.html'
    target=folder/name
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)
    try:
        with os.fdopen(os.open(target,flags,0o600),'wb') as output:
            output.write(content);output.flush();os.fsync(output.fileno())
    except OSError:
        raise WorkspaceHtmlError('OUTPUT_WRITE_FAILED') from None
    return {'status':'CREATED_WORKSPACE_HTML','filename':name,'sha256':hashlib.sha256(content).hexdigest(),'size_bytes':len(content),
            'database_count':workspace['database_count'],'table_count':workspace['table_count'],'contains_table_rows':False,'ready_for_customer_data':False}


def export_synthetic_workspace(output_directory:str | Path)->dict:
    """Two fully generated SQLite files; only rendered HTML remains."""
    with tempfile.TemporaryDirectory(prefix='dbvora-workspace-synthetic-') as tmp:
        a,b=Path(tmp)/'inventory.sqlite',Path(tmp)/'billing.sqlite'
        with closing(sqlite3.connect(a)) as conn:
            conn.executescript("CREATE TABLE suppliers(id INTEGER PRIMARY KEY,name TEXT); CREATE TABLE products(id INTEGER PRIMARY KEY,supplier_id INTEGER REFERENCES suppliers(id),title TEXT); CREATE INDEX products_supplier_idx ON products(supplier_id); INSERT INTO suppliers VALUES(1,'SYNTHETIC_ROW_DO_NOT_EXPORT'); INSERT INTO products VALUES(2,1,'Synthetic Product');")
        with closing(sqlite3.connect(b)) as conn:
            conn.executescript('CREATE TABLE invoices(id INTEGER PRIMARY KEY,total_cents INTEGER); CREATE TABLE payments(id INTEGER PRIMARY KEY,invoice_id INTEGER REFERENCES invoices(id)); INSERT INTO invoices VALUES(5,500); INSERT INTO payments VALUES(6,5);')
        result=export_workspace([a,b],output_directory)
        if b'SYNTHETIC_ROW_DO_NOT_EXPORT' in (Path(output_directory)/result['filename']).read_bytes():
            raise WorkspaceHtmlError('ROW_DATA_IN_REPORT')
        return {**result,'synthetic_only':True,'database_file_retained':False}


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description='Offline multi-SQLite schema workspace')
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--db',action='append',help='Repeat 2-8 absolute local SQLite paths')
    mode.add_argument('--synthetic-only',action='store_true',help='Generate a two-DB demo')
    parser.add_argument('--out',required=True,help='Existing absolute output folder')
    args=parser.parse_args(argv)
    try:
        result=export_synthetic_workspace(args.out) if args.synthetic_only else export_workspace(args.db,args.out)
    except InventoryError as e:
        result={'status':'FAIL_CLOSED','error_code':e.code,'ready_for_customer_data':False}
    except WorkspaceHtmlError as e:
        result={'status':'FAIL_CLOSED','error_code':str(e),'ready_for_customer_data':False}
    except (OSError,sqlite3.Error):
        result={'status':'FAIL_CLOSED','error_code':'SYNTHETIC_WORKSPACE_FAILED','ready_for_customer_data':False}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0 if result['status']=='CREATED_WORKSPACE_HTML' else 1

if __name__=='__main__':
    raise SystemExit(main())

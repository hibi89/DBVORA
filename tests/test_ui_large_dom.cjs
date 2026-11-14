// Synthetic 1,000-table DOM limit regression; no filesystem/DB/customer access.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
  constructor(tag, meter) {
    this.tag = tag; this.meter = meter; this.children = [];
    this.attrs = {}; this.events = {}; this.className = '';
    this._text = ''; this.hidden = false; this.style = {};
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(node => node.textContent).join(''); }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; this._text = ''; }
  setAttribute(k,v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(k,fn) { this.events[k] = fn; }
  getBoundingClientRect() {
    this.meter.rects++;
    return {left:100,top:100,width:120,height:100};
  }
  get classList() {
    return {toggle:(name,active)=>{
      const classes = new Set(this.className.split(/\s+/).filter(Boolean));
      if (active) classes.add(name); else classes.delete(name);
      this.className = [...classes].join(' ');
    }};
  }
}
async function verify() {
  const meter = {rects:0,fetches:0,observationFetches:0};
  const ids = Object.fromEntries([
    'refresh','error','size','tables-count','links-count','db-short','observed',
    'tables','detail','edges','diagram','table-filter','filter-status','filter-empty',
    'database-selector','database-list','workspace-summary','growth-status','growth-scope',
    'growth-history','growth-trend','growth-samples','persistent-growth-status',
    'persistent-growth-trend','persistent-growth-samples','postgres-load','postgres-stats-load','postgres-status','postgres-stats-status','postgres-table-list','postgres-detail'
  ].map(id => [id, new Element('div',meter)]));
  const tables = Array.from({length:1000},(_,i)=>({
    name:`synthetic_table_${String(i).padStart(4,'0')}`,
    columns:[{name:'id',type:'INTEGER',pk_position:1,nullable_declared:false}],
    indexes:[],
    foreign_keys:i>0?[{to_table:`synthetic_table_${String(i-1).padStart(4,'0')}`,
      from_columns:['id'],to_columns:['id']}]:[]
  }));
  const relationships = tables.slice(1).map((table,i)=>({
    from_table:table.name,to_table:tables[i].name,evidence:'declared_foreign_key'
  }));
  const payload={contract_version:'p0-01.v1',engine:'sqlite',db_id:'0123456789abcdefghijklmn',size_bytes:4096,
    observed_at:'2026-11-14T00:00:00Z',tables,relationships};
  const listeners=[];
  const doc={getElementById:id=>ids[id],
    createElement:tag=>new Element(tag,meter),
    createElementNS:(_,tag)=>new Element(tag,meter)};
  const sandbox={document:doc,window:{addEventListener:(name,fn)=>listeners.push({name,fn})},
    ResizeObserver:class{observe(){} disconnect(){}},
    requestAnimationFrame:fn=>fn(),
    fetch:async(url)=>{
      if (url.startsWith('/api/observations?')) {
        meter.observationFetches++;
        return {ok:false,status:404,json:async()=>({})};
      }
      meter.fetches++;
      return {ok:true,status:200,json:async()=>payload};
    },
    Date,Map,Set,String,Number,Intl,console,setTimeout,clearTimeout,AbortController
  };
  const source=fs.readFileSync(path.resolve(__dirname,'../dbvora/web/app.js'),'utf8');
  assert.ok(!/\.innerHTML\s*=/.test(source));
  vm.runInNewContext(source,sandbox);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(ids.tables.children.length,1000);
  assert.equal(ids.edges.children.length,999);
  assert.equal(ids['tables-count'].textContent,'1000');
  assert.equal(ids['filter-status'].textContent,'1000 / 1000 테이블');
  assert.ok(meter.rects <= 1100, 'FK layout must measure each node at most once');
  const firstPath=ids.edges.children[0];
  const beforeSelectionRects=meter.rects;
  for (let i=1;i<50;i++) ids.tables.children[i].events.click();
  assert.equal(ids.edges.children[0],firstPath,
    'table selection must reuse existing SVG edges');
  assert.equal(meter.rects,beforeSelectionRects,
    'selection must not force graph layout reads');
  assert.equal(ids.tables.children[49].getAttribute('aria-pressed'),'true');
  assert.equal(ids.tables.children[48].getAttribute('aria-pressed'),'false');
  ids['table-filter'].value='SYNTHETIC_TABLE_0999';
  ids['table-filter'].events.input();
  assert.equal(ids.tables.children.filter(x=>!x.hidden).length,1);
  assert.equal(ids.edges.children.length,0);
  assert.equal(ids['filter-status'].textContent,'1 / 1000 테이블');
  assert.equal(ids.tables.children[999].getAttribute('aria-pressed'),'true');
  assert.equal(ids.tables.children[49].getAttribute('aria-pressed'),'false');
  ids['table-filter'].value='no-table-here';
  ids['table-filter'].events.input();
  assert.equal(ids.tables.children.filter(x=>!x.hidden).length,0);
  assert.equal(ids['filter-empty'].hidden,false);
  assert.equal(ids.tables.children[999].getAttribute('aria-pressed'),'false');
  ids['table-filter'].value='';
  ids['table-filter'].events.input();
  assert.equal(ids.tables.children.filter(x=>!x.hidden).length,1000);
  assert.equal(ids.edges.children.length,999);
  assert.equal(ids['filter-empty'].hidden,true);
  await ids.refresh.events.click();
  assert.equal(ids.tables.children.length,1000);
  assert.equal(ids.edges.children.length,999);
  assert.equal(meter.fetches,2, 'inventory refresh count stays independent from local observation GETs');
  assert.equal(meter.observationFetches,2, 'initial load and refresh read the local observation route');
  assert.equal(listeners.filter(x=>x.name==='resize').length,1);
  console.log('UI LARGE DOM SIMULATION PASS: 1000 tables, 999 FKs, cached positions, selected edges, filtering, refresh');
}
module.exports={verify};

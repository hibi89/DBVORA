// Lightweight, no-dependency DOM behavior check; not a real browser test.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.attrs = {}; this.events = {}; this.className = ''; this._text = ''; this.hidden = false; this.style = {}; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = [...nodes]; this._text = ''; }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name]; }
  addEventListener(name, fn) { this.events[name] = fn; }
  getBoundingClientRect() { return {left: 100, top: 100, width: 120, height: 100}; }
  get classList() { return {toggle: (name, yes) => { if (yes && !this.className.includes(name)) this.className += ' ' + name; }}; }
}
const ids = Object.fromEntries(['refresh','error','size','tables-count','links-count','db-short','observed','tables','detail','edges','diagram','table-filter','filter-status','filter-empty','database-selector','database-list','database-topology','workspace-summary','growth-status','growth-scope'].map(id => [id, new Element('div')]));
ids.diagram.getBoundingClientRect = () => ({left: 0, top: 0, width: 800, height: 600});
const doc = {getElementById: id => ids[id], createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag)};
const marker = '<img src=x onerror=alert(7)>';
const data = {contract_version:'p0-01.v1',engine:'sqlite',db_id:'abc12345678901234567890',size_bytes:12345, observed_at:'2026-10-26T07:00:00Z',
  relationships:[{from_table:'orders',to_table:'customers',from_columns:['customer_id'],to_columns:['id'],evidence:'declared_foreign_key'}],
  tables:[
    {name:'customers', columns:[{name:'id',type:'INTEGER',pk_position:1,nullable_declared:true}],indexes:[],foreign_keys:[]},
    {name:'orders', columns:[{name:'customer_id',type:'INTEGER',pk_position:0,nullable_declared:false}],indexes:[],foreign_keys:[{to_table:'customers',from_columns:['customer_id'],to_columns:['id']}]},
    {name:marker, columns:[{name:'<svg onload=alert(9)>',type:'TEXT',pk_position:0,nullable_declared:true}],indexes:[],foreign_keys:[]}
  ]};
const listeners = [];
let failNextFetch = false;
let storageFetches = 0;
let currentInventory = data;
const sandbox = {
  document:doc, window:{addEventListener(name, fn){ listeners.push({name, fn}); }}, ResizeObserver:class {observe(){} disconnect(){}},
  requestAnimationFrame: fn => fn(),
  fetch: async (url) => {
    if (failNextFetch) { failNextFetch = false; throw new TypeError('Failed to fetch'); }
    if (url.startsWith('/api/table-storage?')) {
      storageFetches++;
      return {ok:true,json: async () => ({
        contract: 'dbvora.local-table-storage.v1', table: new URL(url, 'http://127.0.0.1').searchParams.get('table'),
        scope: 'logical_btree_pages_dbstat_including_indexes_wal_pages_possible',
        metric: {status:'measured', allocated_btree_bytes:8192, source:'sqlite_dbstat_aggregate'}
      })};
    }
    return {ok:true,json: async () => currentInventory};
  },
  setTimeout, clearTimeout, AbortController,
  console, Date, Map, Number, String, Intl
};
const script = fs.readFileSync(path.resolve(__dirname, '../dbvora/web/app.js'), 'utf8');
assert.ok(!/\.innerHTML\s*=/.test(script));
vm.runInNewContext(script, sandbox);
setImmediate(async () => {
  try {
    assert.equal(ids.tables.children.length, 3);
    assert.equal(ids['database-selector'].hidden, true, 'single DB must hide chooser');
    assert.ok(ids['growth-status'].textContent.includes('첫 측정'), 'baseline no fabricated trend');
    assert.equal(ids['database-topology'].children.length, 0, 'single DB topology remains hidden');
    assert.equal(ids['tables-count'].textContent, '3');
    assert.equal(ids['links-count'].textContent, '1');
    assert.equal(ids.edges.children.length, 1);
    assert.ok(ids.detail.textContent.includes('customers'));
    assert.equal(storageFetches, 0, 'dbstat must never scan automatically');
    const getMeasure = () => ids.detail.children.flatMap(root => {
      const items = [];
      const walk = node => { if (node.className.split(/\s+/).includes('storage-measure')) items.push(node);
                             node.children.forEach(walk); };
      walk(root); return items;
    })[0];
    assert.ok(getMeasure(), 'inspector must expose opt-in measurement');
    await getMeasure().events.click();
    assert.equal(storageFetches, 1, 'explicit click starts one local measurement');
    assert.ok(ids.detail.textContent.includes('8 KB'), 'display measured allocated btree pages');
    ids.tables.children[1].events.click();
    assert.ok(ids.detail.textContent.includes('customer_id'));
    ids.tables.children[2].events.click();
    assert.ok(ids.detail.textContent.includes(marker));
    assert.ok(ids.detail.textContent.includes('<svg onload=alert(9)>'));
    const allTags = node => [node.tag,...node.children.flatMap(allTags)];
    assert.ok(!allTags(ids.detail).includes('img'));
    assert.equal(ids.error.hidden, true);
    ids['table-filter'].value = 'ORDERS';
    ids['table-filter'].events.input();
    assert.equal(ids.tables.children.filter(x => !x.hidden).length, 1, 'case-insensitive filtering');
    assert.ok(ids.detail.textContent.includes('orders'), 'visible selected inspector');
    assert.equal(ids.edges.children.length, 0, 'filtered relationship cannot draw a phantom edge');
    ids['table-filter'].value = '<img';
    ids['table-filter'].events.input();
    assert.equal(ids.tables.children.filter(x => !x.hidden).length, 1, 'inert untrusted table name');
    assert.ok(ids.detail.textContent.includes(marker));
    ids['table-filter'].value = 'does-not-exist';
    ids['table-filter'].events.input();
    assert.equal(ids.tables.children.filter(x => !x.hidden).length, 0);
    assert.equal(ids['filter-empty'].hidden, false);
    assert.ok(ids.detail.textContent.includes('검색 결과'));
    ids['table-filter'].value = '';
    ids['table-filter'].events.input();
    assert.equal(ids.tables.children.filter(x => !x.hidden).length, 3);
    assert.equal(ids['filter-empty'].hidden, true);
    assert.equal(ids.edges.children.length, 1);
    const resizeCount = () => listeners.filter(listener => listener.name === 'resize').length;
    assert.equal(resizeCount(), 1, 'initial render must install exactly one resize listener');
    currentInventory = {...data, size_bytes: data.size_bytes + 2048,
      observed_at: '2026-10-26T07:05:00Z'};
    await ids.refresh.events.click();
    assert.ok(ids['growth-status'].textContent.includes('증가 +2 KB'),
      'show measured two-sample main-file delta');
    await ids.refresh.events.click();
    assert.ok(ids['growth-status'].textContent.includes('비교 불가'),
      'equal-time comparison cannot be claimed as growth');
    assert.equal(resizeCount(), 1, 'repeated refresh must not accumulate resize listeners');
    assert.equal(ids.tables.children.length, 3);
    assert.equal(ids.edges.children.length, 1);
    ids['table-filter'].value = 'CUSTOMERS';
    ids['table-filter'].events.input();
    await ids.refresh.events.click();
    assert.equal(ids.tables.children.filter(x => !x.hidden).length, 1, 'filter persists after refresh');
    const inspectorBeforeDisconnect = ids.detail.textContent;
    const growthBeforeDisconnect = ids['growth-status'].textContent;
    failNextFetch = true;
    await ids.refresh.events.click();
    assert.equal(ids.refresh.disabled, false, 'network failure must enable refresh');
    assert.equal(ids.error.hidden, false, 'network failure must be visible');
    assert.ok(ids.error.textContent.includes('연결이 중단'), 'network failure is actionable');
    assert.equal(ids.detail.textContent, inspectorBeforeDisconnect,
      'network failure must keep last verified inspector');
    assert.equal(ids['growth-status'].textContent, growthBeforeDisconnect,
      'network failure must never record an invented measurement');
    assert.equal(ids.tables.children.filter(x => !x.hidden).length, 1,
      'network failure must preserve local filter');
    await ids.refresh.events.click();
    assert.equal(ids.error.hidden, true, 'successful retry clears network error');
    assert.equal(ids.tables.children.filter(x => !x.hidden).length, 1);
    await require('./test_ui_large_dom.cjs').verify();
    require('./test_workspace_html_dom.cjs').verify();
    console.log('UI DOM SIMULATION PASS: schema, XSS identifiers and resize listener idempotence');
  } catch(e) { console.error(e); process.exitCode=1; }
});

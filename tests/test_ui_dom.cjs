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
const ids = Object.fromEntries(['refresh','error','size','tables-count','links-count','db-short','observed','tables','detail','edges','diagram','table-filter','filter-status','filter-empty'].map(id => [id, new Element('div')]));
ids.diagram.getBoundingClientRect = () => ({left: 0, top: 0, width: 800, height: 600});
const doc = {getElementById: id => ids[id], createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag)};
const marker = '<img src=x onerror=alert(7)>';
const data = {engine:'sqlite',db_id:'abc12345678901234567890',size_bytes:12345, observed_at:'2026-10-26T07:00:00Z',
  relationships:[{from_table:'orders',to_table:'customers',from_columns:['customer_id'],to_columns:['id'],evidence:'declared_foreign_key'}],
  tables:[
    {name:'customers', columns:[{name:'id',type:'INTEGER',pk_position:1,nullable_declared:true}],indexes:[],foreign_keys:[]},
    {name:'orders', columns:[{name:'customer_id',type:'INTEGER',pk_position:0,nullable_declared:false}],indexes:[],foreign_keys:[{to_table:'customers',from_columns:['customer_id'],to_columns:['id']}]},
    {name:marker, columns:[{name:'<svg onload=alert(9)>',type:'TEXT',pk_position:0,nullable_declared:true}],indexes:[],foreign_keys:[]}
  ]};
const listeners = [];
const sandbox = {
  document:doc, window:{addEventListener(name, fn){ listeners.push({name, fn}); }}, ResizeObserver:class {observe(){} disconnect(){}},
  requestAnimationFrame: fn => fn(), fetch: async () => ({ok:true,json: async () => data}),
  console, Date, Map, Number, String, Intl
};
const script = fs.readFileSync(path.resolve(__dirname, '../dbvora/web/app.js'), 'utf8');
assert.ok(!/\.innerHTML\s*=/.test(script));
vm.runInNewContext(script, sandbox);
setImmediate(async () => {
  try {
    assert.equal(ids.tables.children.length, 3);
    assert.equal(ids['tables-count'].textContent, '3');
    assert.equal(ids['links-count'].textContent, '1');
    assert.equal(ids.edges.children.length, 1);
    assert.ok(ids.detail.textContent.includes('customers'));
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
    await ids.refresh.events.click();
    await ids.refresh.events.click();
    assert.equal(resizeCount(), 1, 'repeated refresh must not accumulate resize listeners');
    assert.equal(ids.tables.children.length, 3);
    assert.equal(ids.edges.children.length, 1);
    ids['table-filter'].value = 'CUSTOMERS';
    ids['table-filter'].events.input();
    await ids.refresh.events.click();
    assert.equal(ids.tables.children.filter(x => !x.hidden).length, 1, 'filter persists after refresh');
    require('./test_workspace_html_dom.cjs').verify();
    console.log('UI DOM SIMULATION PASS: schema, XSS identifiers and resize listener idempotence');
  } catch(e) { console.error(e); process.exitCode=1; }
});

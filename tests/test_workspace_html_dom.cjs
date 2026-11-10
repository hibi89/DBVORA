// Offline workspace graph regression. Exercises actual _PAGE JavaScript in a lightweight DOM.
// No network, browser, customer DB, or new dependency. Not real-browser proof.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {TextDecoder} = require('node:util');

class Element {
  constructor(tag) { this.tag=tag;this.children=[];this.attrs={};this.events={};this._text=''; }
  set textContent(text) { this._text=String(text);this.children=[]; }
  get textContent() { return this._text+this.children.map(el=>el.textContent).join(''); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children=[...children];this._text=''; }
  setAttribute(name,value) { this.attrs[name]=String(value); }
  addEventListener(event,fn) { this.events[event]=fn; }
}
const IDS=['summary','databases','tables','graph','relationships','details','cross-links','schema-review'];
const fakeTable = name => ({
  name,columns:[{name:'id',type:'INTEGER',pk_position:1}],indexes:[],foreign_keys:[],
  storage:{status:'unavailable'}
});
const graphEdge = (from,to,present) => ({
  database_id:'db1',from_table:from,to_table:to,from_columns:['id'],
  to_columns:['id'],target_in_inventory:present
});

function runOfflineWorkspace(source,overrides) {
  const template=source.match(/_PAGE = '''([\s\S]*?)'''/);
  assert.ok(template,'Python _PAGE literal is present');
  const script=template[1].match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(script,'self-contained script exists');
  const payload={
    contract_version:'p0-03.workspace.v1',database_count:2,table_count:2,
    total_main_db_size_bytes:12345,relationships:[],
    databases:[
      {db_id:'db1',label:'Database 1',size_bytes:12345,tables:[fakeTable('Parent'),fakeTable('child')]},
      {db_id:'db2',label:'Database 2',size_bytes:0,tables:[]}
    ],
    declared_cross_database_links:[],schema_review:{status:'UNAVAILABLE'},...overrides
  };
  const data=Buffer.from(JSON.stringify(payload),'utf8').toString('base64');
  const js=script[1].replace('const encodedWorkspace="__BASE64__";',
                             'const encodedWorkspace='+JSON.stringify(data)+';');
  assert.ok(!js.includes('__BASE64__'),'workspace fixture injected');
  const ids=Object.fromEntries(IDS.map(id=>[id,new Element('div')]));
  const document={
    getElementById:id=>{assert.ok(ids[id],'Unknown DOM id '+id);return ids[id];},
    createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)
  };
  vm.runInNewContext(js,{document,TextDecoder,Uint8Array,atob},{timeout:1000});
  return ids;
}

function verify(sourceFile=path.resolve(__dirname,'../dbvora/workspace_html.py')) {
  const source=fs.readFileSync(sourceFile,'utf8');
  const ascii=runOfflineWorkspace(source,{relationships:[graphEdge('child','PARENT',true)]});
  assert.equal(ascii.graph.children.filter(x=>x.tag==='line').length,1,
               'ASCII case-insensitive FK target must draw exactly one relationship');
  assert.ok(ascii.relationships.textContent.includes('declared FK'));

  const unicode=runOfflineWorkspace(source,{
    databases:[
      {db_id:'db1',label:'Database 1',size_bytes:12345,tables:[fakeTable('ÄParent'),fakeTable('child')]},
      {db_id:'db2',label:'Database 2',size_bytes:0,tables:[]}
    ],
    relationships:[graphEdge('child','äParent',false)]
  });
  assert.equal(unicode.graph.children.filter(x=>x.tag==='line').length,0,
               'non-ASCII different identifiers must not produce fabricated edges');
  assert.ok(unicode.relationships.textContent.includes('target absent'));

  const unchanged=runOfflineWorkspace(source,{relationships:[graphEdge('child','Parent',true)]});
  assert.equal(unchanged.graph.children.filter(x=>x.tag==='line').length,1);

  const malicious='<img src=x onerror=alert(1)>';
  const special=runOfflineWorkspace(source,{
    databases:[
      {db_id:'db1',label:'Database 1',size_bytes:12345,tables:[fakeTable(malicious),fakeTable('child')]},
      {db_id:'db2',label:'Database 2',size_bytes:0,tables:[]}
    ],relationships:[graphEdge('child',malicious,true)]
  });
  assert.equal(special.graph.children.filter(x=>x.tag==='line').length,1);
  assert.ok(special.graph.children.some(x=>x.tag==='text'&&x.textContent===malicious.slice(0,22)+'…'));
  assert.ok(!special.graph.children.some(x=>x.tag==='img'),'identifier must remain text');

  console.log('OFFLINE WORKSPACE GRAPH DOM PASS: ASCII FK, Unicode distinction, exact FK, escaped labels');
}
module.exports={verify};
if(require.main===module)verify();

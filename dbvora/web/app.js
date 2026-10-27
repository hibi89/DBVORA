'use strict';
// No innerHTML and no identifiers used as HTML/JS/CSS selectors.
// All externally sourced schema names become text nodes only.
const $ = (id) => document.getElementById(id);
const SVG = 'http://www.w3.org/2000/svg';
let inventory = null;
let selected = null;
let nodeElements = new Map();
let observer = null;

function el(tag, klass, content) {
  const node = document.createElement(tag);
  if (klass) node.className = klass;
  if (content !== undefined) node.textContent = String(content);
  return node;
}
function formatBytes(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let n = value, index = 0;
  while (n >= 1024 && index < units.length - 1) { n /= 1024; index++; }
  return `${n.toLocaleString('en-US', {maximumFractionDigits: index ? 2 : 0})} ${units[index]}`;
}
function clear(node) { node.replaceChildren(); }
function displayError(message) { const area = $('error'); area.textContent = message; area.hidden = false; }
function hideError() { $('error').hidden = true; }
function badge(text, klass) { return el('span', `mini-badge ${klass || ''}`, text); }

function inspect(tableName) {
  if (!inventory) return;
  const table = inventory.tables.find((item) => item.name === tableName);
  if (!table) return;
  selected = tableName;
  for (const [name, button] of nodeElements) {
    const isActive = name === tableName;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-pressed', String(isActive));
  }
  const details = $('detail');
  clear(details);
  const title = el('div', 'detail-heading');
  title.append(el('div', 'detail-icon', '▦'));
  const titleText = el('div');
  titleText.append(el('span', 'detail-kicker', 'SELECTED TABLE'), el('h3', '', table.name));
  title.append(titleText);
  details.append(title);
  const meta = el('div', 'detail-meta');
  meta.append(badge(`${table.columns.length} COLUMNS`, 'neutral'), badge(`${table.indexes.length} INDEXES`, 'neutral'), badge(`${table.foreign_keys.length} FOREIGN KEYS`, 'neutral'));
  details.append(meta);
  details.append(el('h4', 'section-label', 'COLUMNS'));
  const cols = el('div', 'columns');
  for (const field of table.columns) {
    const row = el('div', 'column-row');
    const left = el('div', 'column-name');
    left.append(el('span', 'column-square', field.pk_position ? '◆' : '◇'), el('span', 'column-identifier', field.name));
    if (field.pk_position) left.append(badge('PK', 'primary'));
    const right = el('div', 'column-type', field.type || 'ANY');
    row.append(left, right);
    const property = el('span', 'column-property', field.nullable_declared ? 'NULL 허용 선언' : 'NOT NULL 선언');
    row.append(property);
    cols.append(row);
  }
  if (!table.columns.length) cols.append(el('p', 'empty-state', '컬럼 정보 없음'));
  details.append(cols);
  details.append(el('h4', 'section-label', 'INDEXES'));
  const indexes = el('div', 'info-list');
  for (const index of table.indexes) {
    const line = el('div', 'info-row');
    const info = el('div');
    info.append(el('strong', '', index.name));
    info.append(el('small', '', index.key_columns.map((item) => item === null ? '(expression)' : item).join(', ') || '—'));
    line.append(info, badge(index.unique ? 'UNIQUE' : 'INDEX', 'neutral'));
    indexes.append(line);
  }
  if (!table.indexes.length) indexes.append(el('p', 'empty-state', '인덱스 없음'));
  details.append(indexes);
  details.append(el('h4', 'section-label', 'FOREIGN KEYS'));
  const keys = el('div', 'info-list');
  for (const fk of table.foreign_keys) {
    const line = el('div', 'info-row');
    const info = el('div');
    info.append(el('strong', '', fk.to_table));
    info.append(el('small', '', `${fk.from_columns.join(', ')} → ${fk.to_columns.map((x) => x || '(PK)').join(', ')}`));
    line.append(info, badge('DECLARED', 'primary'));
    keys.append(line);
  }
  if (!table.foreign_keys.length) keys.append(el('p', 'empty-state', '선언된 외래키 없음'));
  details.append(keys);
  drawEdges();
}

function drawEdges() {
  const svg = $('edges');
  clear(svg);
  if (!inventory) return;
  const board = $('diagram').getBoundingClientRect();
  if (!board.width || !board.height) return;
  svg.setAttribute('viewBox', `0 0 ${board.width} ${board.height}`);
  for (const link of inventory.relationships) {
    if (link.evidence !== 'declared_foreign_key') continue;
    const from = nodeElements.get(link.from_table);
    const to = nodeElements.get(link.to_table);
    if (!from || !to) continue;
    const a = from.getBoundingClientRect(), b = to.getBoundingClientRect();
    const x1 = a.left + a.width / 2 - board.left;
    const x2 = b.left + b.width / 2 - board.left;
    const y1 = a.top + a.height / 2 - board.top;
    const y2 = b.top + b.height / 2 - board.top;
    const bend = Math.max(35, Math.abs(y2-y1) * .65);
    const path = document.createElementNS(SVG, 'path');
    path.setAttribute('d', `M ${x1} ${y1} C ${x1} ${y1 - bend}, ${x2} ${y2 + bend}, ${x2} ${y2}`);
    path.setAttribute('class', selected === link.from_table || selected === link.to_table ? 'edge active' : 'edge');
    svg.append(path);
  }
}

function render(data) {
  inventory = data;
  $('size').textContent = formatBytes(data.size_bytes);
  $('tables-count').textContent = String(data.tables.length);
  $('links-count').textContent = String(data.relationships.filter((r) => r.evidence === 'declared_foreign_key').length);
  $('db-short').textContent = `${data.engine.toUpperCase()} · ${data.db_id.slice(0, 8)}`;
  $('observed').textContent = `OBSERVED ${new Date(data.observed_at).toLocaleString('ko-KR')}`;
  const grid = $('tables');
  clear(grid); nodeElements = new Map();
  for (const table of data.tables) {
    const card = el('button', 'table-node');
    card.type = 'button';
    card.setAttribute('aria-label', `${table.name} 테이블 상세보기`);
    card.setAttribute('aria-pressed', 'false');
    const header = el('span', 'node-top');
    header.append(el('span', 'table-symbol', '▤'), el('span', 'node-count', `${table.columns.length} COL`));
    card.append(header, el('strong', 'table-name', table.name), el('span', 'node-bottom', `${table.foreign_keys.length} FK · ${table.indexes.length} IDX`));
    card.addEventListener('click', () => inspect(table.name));
    grid.append(card);
    nodeElements.set(table.name, card);
  }
  if (!data.tables.length) grid.append(el('p', 'placeholder', '이 데이터베이스에는 사용자 테이블이 없습니다.'));
  if (selected && nodeElements.has(selected)) inspect(selected);
  else if (data.tables.length) inspect(data.tables[0].name);
  else { selected = null; clear($('detail')); $('detail').append(el('p', 'empty-state', '검사할 테이블이 없습니다.')); }
  requestAnimationFrame(drawEdges);
  if (observer) observer.disconnect();
  observer = new ResizeObserver(drawEdges);
  observer.observe($('diagram'));

}

// Register exactly once; render() may run on every manual refresh.
window.addEventListener('resize', drawEdges, {passive: true});

async function refresh() {
  const btn = $('refresh');
  btn.disabled = true;
  hideError();
  try {
    const response = await fetch('/api/inventory', {cache: 'no-store', credentials: 'same-origin'});
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error?.message || '메타데이터를 읽을 수 없습니다.');
    render(data);
  } catch (error) { displayError(error.message || '연결 실패'); }
  finally { btn.disabled = false; }
}
$('refresh').addEventListener('click', refresh);
refresh();

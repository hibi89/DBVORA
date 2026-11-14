'use strict';
// No innerHTML and no identifiers used as HTML/JS/CSS selectors.
// All externally sourced schema names become text nodes only.
const $ = (id) => document.getElementById(id);
const SVG = 'http://www.w3.org/2000/svg';
let inventory = null;
let workspace = null;
let selectedDatabase = null;
let selected = null;
// Strictly in-memory: no localStorage, disk writes, background collection or network calls.
let lastMeasurements = new Map();
let growthComparisons = new Map();
let nodeElements = new Map();
let edgeByTable = new Map();
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

// Compare only two verified server observations of the same DB identity.
// The main-file byte delta does not include WAL/SHM and is not a forecast.
function recordMeasurements(data) {
  const databases = data.contract_version === 'p0-03.workspace.v1'
    ? data.databases : [data];
  const next = new Map();
  const comparisons = new Map();
  for (const db of databases) {
    const timestamp = Date.parse(db.observed_at);
    if (typeof db.db_id !== 'string' || !Number.isSafeInteger(db.size_bytes) ||
        db.size_bytes < 0 || !Number.isFinite(timestamp)) continue;
    const prior = lastMeasurements.get(db.db_id);
    if (prior && timestamp > prior.timestamp) {
      comparisons.set(db.db_id, {status: 'measured',
        delta: db.size_bytes - prior.size_bytes});
    } else if (prior) {
      comparisons.set(db.db_id, {status: 'unavailable'});
    } else {
      comparisons.set(db.db_id, {status: 'baseline'});
    }
    next.set(db.db_id, {size_bytes: db.size_bytes, timestamp});
  }
  // Enforce a bounded memory footprint (<= 8 server-selected DBs).
  lastMeasurements = next;
  growthComparisons = comparisons;
}

function displayGrowth() {
  const id = workspace ? selectedDatabase : inventory?.db_id;
  const comparison = growthComparisons.get(id);
  const target = $('growth-status');
  if (!comparison || comparison.status === 'baseline') {
    target.textContent = '첫 측정 완료 · 새로고침 후 비교';
  } else if (comparison.status !== 'measured') {
    target.textContent = '비교 불가 · 관측 시간이 증가하지 않음';
  } else if (comparison.delta === 0) {
    target.textContent = '직전 측정 대비 변화 없음 (0 B)';
  } else {
    const sign = comparison.delta > 0 ? '증가 +' : '감소 -';
    target.textContent = '직전 측정 대비 ' + sign + formatBytes(Math.abs(comparison.delta));
  }
}

// Updating the selected table must not rebuild hundreds of SVG paths.
function highlightEdges(tableName, active) {
  if (tableName === null) return;
  for (const edge of edgeByTable.get(tableName) || []) {
    edge.setAttribute('class', active ? 'edge active' : 'edge');
  }
}

function inspect(tableName) {
  if (!inventory) return;
  const table = inventory.tables.find((item) => item.name === tableName);
  if (!table) return;
  const previous = nodeElements.get(selected);
  if (previous) {
    previous.classList.toggle('active', false);
    previous.setAttribute('aria-pressed', 'false');
  }
  highlightEdges(selected, false);
  selected = tableName;
  const current = nodeElements.get(selected);
  if (current) {
    current.classList.toggle('active', true);
    current.setAttribute('aria-pressed', 'true');
  }
  highlightEdges(selected, true);
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
  const storage = el('section', 'storage-measurement');
  storage.append(el('h4', 'section-label', 'ALLOCATED BTREE PAGES'));
  storage.append(el('p', 'storage-note', 'SQLite dbstat 기준 할당된 B-tree 페이지(인덱스 포함). 실제 디스크 사용량 또는 데이터 행 크기가 아닙니다.'));
  const measure = el('button', 'storage-measure', '테이블 용량 측정');
  measure.type = 'button';
  const storageStatus = el('p', 'storage-status', '측정 전 · 버튼을 눌러야 조회합니다.');
  storageStatus.setAttribute('role', 'status');
  storageStatus.setAttribute('aria-live', 'polite');
  measure.addEventListener('click', async () => {
    measure.disabled = true;
    storageStatus.textContent = '측정 중…';
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 8000);
    try {
      const dbQuery = workspace ? '&database=' + encodeURIComponent(selectedDatabase) : '';
      const response = await fetch('/api/table-storage?table=' + encodeURIComponent(table.name) + dbQuery, {
        cache: 'no-store', credentials: 'same-origin', signal: controller.signal
      });
      if (!response.ok) throw new Error('measurement_unavailable');
      const data = await response.json();
      const metric = data?.metric;
      if (data?.contract !== 'dbvora.local-table-storage.v1' || data.table !== table.name
          || typeof data.scope !== 'string' || !data.scope.includes('dbstat')) {
        throw new Error('measurement_contract_mismatch');
      }
      if (metric?.status === 'measured' && Number.isSafeInteger(metric.allocated_btree_bytes)
          && metric.allocated_btree_bytes >= 0) {
        storageStatus.textContent = '할당된 B-tree 페이지: ' + formatBytes(metric.allocated_btree_bytes);
      } else if (metric?.status === 'unavailable') {
        storageStatus.textContent = '측정 불가 · dbstat 또는 용량/시간 제한';
      } else {
        throw new Error('measurement_invalid');
      }
    } catch (_error) {
      storageStatus.textContent = '측정 실패 · DB 상태 확인 후 다시 시도하세요.';
    } finally {
      clearTimeout(deadline);
      measure.disabled = false;
    }
  });
  storage.append(measure, storageStatus);
  details.append(storage);
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
}

function drawEdges() {
  const svg = $('edges');
  clear(svg);
  edgeByTable = new Map();
  if (!inventory) return;
  const board = $('diagram').getBoundingClientRect();
  if (!board.width || !board.height) return;
  svg.setAttribute('viewBox', `0 0 ${board.width} ${board.height}`);
  // Compute each visible table's position once even when it has many FKs.
  const rectangles = new Map();
  const position = (name, element) => {
    if (!rectangles.has(name)) rectangles.set(name, element.getBoundingClientRect());
    return rectangles.get(name);
  };
  const paths = [];
  for (const link of inventory.relationships) {
    if (link.evidence !== 'declared_foreign_key') continue;
    const from = nodeElements.get(link.from_table);
    const to = nodeElements.get(link.to_table);
    if (!from || !to || from.hidden || to.hidden) continue;
    const a = position(link.from_table, from);
    const b = position(link.to_table, to);
    const x1 = a.left + a.width / 2 - board.left;
    const x2 = b.left + b.width / 2 - board.left;
    const y1 = a.top + a.height / 2 - board.top;
    const y2 = b.top + b.height / 2 - board.top;
    const bend = Math.max(35, Math.abs(y2-y1) * .65);
    const path = document.createElementNS(SVG, 'path');
    path.setAttribute('d', `M ${x1} ${y1} C ${x1} ${y1 - bend}, ${x2} ${y2 + bend}, ${x2} ${y2}`);
    path.setAttribute('class', selected === link.from_table || selected === link.to_table ? 'edge active' : 'edge');
    paths.push(path);
    for (const name of new Set([link.from_table, link.to_table])) {
      if (!edgeByTable.has(name)) edgeByTable.set(name, []);
      edgeByTable.get(name).push(path);
    }
  }
  if (paths.length) svg.append(...paths);
}

// Filter only the already loaded schema names. Never transmit a query or fetch rows.
function applyFilter() {
  if (!inventory) return;
  const query = String($('table-filter').value || '').trim().toLocaleLowerCase();
  let count = 0;
  let first = null;
  for (const [name, button] of nodeElements) {
    const show = name.toLocaleLowerCase().includes(query);
    button.hidden = !show;
    if (show) { count++; if (first === null) first = name; }
  }
  $('filter-status').textContent = `${count} / ${nodeElements.size} 테이블`;
  $('filter-empty').hidden = count !== 0 || nodeElements.size === 0;
  if (count === 0) {
    const prior = nodeElements.get(selected);
    if (prior) {
      prior.classList.toggle('active', false);
      prior.setAttribute('aria-pressed', 'false');
    }
    selected = null;
    clear($('detail'));
    $('detail').append(el('p', 'empty-state', query ? '검색 결과가 없습니다.' : '검사할 테이블이 없습니다.'));
  } else if (!selected || nodeElements.get(selected)?.hidden) {
    inspect(first);
  }
  drawEdges();
}

// Multi-workspace relationships are scoped by DB identity, never joined by
// shared table name. Only the active DB's cards/SVG paths are rendered.
function showWorkspaceDatabase(dbId) {
  if (!workspace) return;
  const database = workspace.databases.find((db) => db.db_id === dbId);
  if (!database) return;
  if (selectedDatabase !== dbId) selected = null;
  selectedDatabase = dbId;
  const localLinks = workspace.relationships.filter((link) =>
    link.database_id === dbId && link.evidence === 'declared_foreign_key' &&
    link.target_in_inventory === true);
  renderSingle({...database, relationships: localLinks});
  for (const button of $('database-list').children) {
    button.setAttribute('aria-pressed', button.dataset.dbId === dbId ? 'true' : 'false');
  }
  displayGrowth();
}

function render(data) {
  if (data?.contract_version === 'p0-03.workspace.v1') {
    if (!Array.isArray(data.databases) || data.databases.length < 2 ||
        !Array.isArray(data.relationships)) throw new Error('Invalid workspace metadata');
    workspace = data;
    $('database-selector').hidden = false;
    $('workspace-summary').textContent =
      `${data.database_count} DB · ${data.table_count} 테이블 · 합계 ${formatBytes(data.total_main_db_size_bytes)}`;
    const chooser = $('database-list');
    clear(chooser);
    for (const db of data.databases) {
      const button = el('button', 'database-choice');
      button.type = 'button';
      button.dataset.dbId = db.db_id;
      button.setAttribute('aria-label', db.label + ' 데이터베이스 선택');
      button.append(el('strong', '', db.label), el('span', '', `${db.tables.length} 테이블 · ${formatBytes(db.size_bytes)}`));
      button.addEventListener('click', () => showWorkspaceDatabase(db.db_id));
      chooser.append(button);
    }
    if (!data.databases.some((db) => db.db_id === selectedDatabase)) {
      selectedDatabase = null;
      selected = null;
    }
    showWorkspaceDatabase(selectedDatabase || data.databases[0].db_id);
  } else if (data?.contract_version === 'p0-01.v1') {
    workspace = null;
    selectedDatabase = null;
    $('database-selector').hidden = true;
    renderSingle(data);
  } else {
    throw new Error('Unsupported inventory metadata');
  }
}

function renderSingle(data) {
  inventory = data;
  $('size').textContent = formatBytes(data.size_bytes);
  $('tables-count').textContent = String(data.tables.length);
  $('links-count').textContent = String(data.relationships.filter((r) => r.evidence === 'declared_foreign_key').length);
  $('db-short').textContent = `${data.engine.toUpperCase()} · ${data.db_id.slice(0, 8)}`;
  $('observed').textContent = `OBSERVED ${new Date(data.observed_at).toLocaleString('ko-KR')}`;
  const grid = $('tables');
  clear(grid); nodeElements = new Map();
  const cards = [];
  for (const table of data.tables) {
    const card = el('button', 'table-node');
    card.type = 'button';
    card.setAttribute('aria-label', `${table.name} 테이블 상세보기`);
    card.setAttribute('aria-pressed', 'false');
    const header = el('span', 'node-top');
    header.append(el('span', 'table-symbol', '▤'), el('span', 'node-count', `${table.columns.length} COL`));
    card.append(header, el('strong', 'table-name', table.name), el('span', 'node-bottom', `${table.foreign_keys.length} FK · ${table.indexes.length} IDX`));
    card.addEventListener('click', () => inspect(table.name));
    cards.push(card);
    nodeElements.set(table.name, card);
  }
  if (cards.length) grid.append(...cards);
  if (!data.tables.length) grid.append(el('p', 'placeholder', '이 데이터베이스에는 사용자 테이블이 없습니다.'));
  if (selected && nodeElements.has(selected)) inspect(selected);
  else if (data.tables.length) inspect(data.tables[0].name);
  else { selected = null; clear($('detail')); $('detail').append(el('p', 'empty-state', '검사할 테이블이 없습니다.')); }
  applyFilter();
  if (observer) observer.disconnect();
  observer = new ResizeObserver(drawEdges);
  observer.observe($('diagram'));

}

// Register exactly once; render() may run on every manual refresh.
window.addEventListener('resize', drawEdges, {passive: true});

// Never leave Refresh disabled indefinitely if localhost stops responding.
// Keep the last verified inventory, filter and inspector on transport failure.
const INVENTORY_TIMEOUT_MS = 15000;
let refreshPending = false;

async function refresh() {
  if (refreshPending) return; // Do not permit overlapping/stale responses.
  refreshPending = true;
  const btn = $('refresh');
  btn.disabled = true;
  hideError();
  const controller = new AbortController();
  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, INVENTORY_TIMEOUT_MS);
  try {
    const response = await fetch('/api/inventory', {
      cache: 'no-store', credentials: 'same-origin', signal: controller.signal
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error?.message || '메타데이터를 읽을 수 없습니다.');
    render(data);
    recordMeasurements(data);
    displayGrowth();
  } catch (error) {
    if (timedOut) displayError('메타데이터 요청 시간이 초과되었습니다. 다시 시도하세요.');
    else if (error?.name === 'TypeError' || error?.name === 'AbortError') {
      displayError('연결이 중단되었습니다. 다시 시도하세요.');
    } else displayError(error?.message || '연결 실패');
  } finally {
    clearTimeout(timeout);
    refreshPending = false;
    btn.disabled = false;
  }
}
$('refresh').addEventListener('click', refresh);
$('table-filter').addEventListener('input', applyFilter);
refresh();

"""Validate explicitly user-declared cross-DB metadata links; NEVER infer joins.

A declared link is structural intent only. No cross-database SQL is run and no
record-level relationship, key constraint, or writer provenance is asserted.
"""
from __future__ import annotations

from dbvora.errors import InventoryError

MAX_DECLARED_LINKS = 64
_FIELDS = frozenset({'from_db', 'from_table', 'from_column', 'to_db', 'to_table', 'to_column'})


def attach_declared_links(workspace: dict, declarations: list[dict]) -> dict:
    if (not isinstance(workspace, dict) or workspace.get('contract_version') != 'p0-03.workspace.v1'
            or type(workspace.get('databases')) is not list):
        raise InventoryError('INVALID_WORKSPACE', 'Cannot attach links to an invalid workspace.')
    if type(declarations) is not list or len(declarations) > MAX_DECLARED_LINKS:
        raise InventoryError('INVALID_LINK_COUNT', 'Provide no more than 64 explicit metadata links.')
    databases = workspace['databases']
    valid = []
    fingerprints = set()
    for entry in declarations:
        if type(entry) is not dict or set(entry) != _FIELDS:
            raise InventoryError('INVALID_LINK', 'Link declaration has invalid fields.')
        first, last = entry['from_db'], entry['to_db']
        if (type(first) is not int or type(last) is not int or first == last
                or not 1 <= first <= len(databases) or not 1 <= last <= len(databases)):
            raise InventoryError('INVALID_LINK_ENDPOINT', 'Link database positions are invalid.')
        start, end = databases[first - 1], databases[last - 1]
        selected = []
        for db, table_field, col_field in ((start, 'from_table', 'from_column'),
                                           (end, 'to_table', 'to_column')):
            table_name, column_name = entry[table_field], entry[col_field]
            if type(table_name) is not str or type(column_name) is not str:
                raise InventoryError('INVALID_LINK_ENDPOINT', 'Link names must be strings.')
            tables = [table for table in db['tables'] if table['name'] == table_name]
            if len(tables) != 1 or not any(c['name'] == column_name for c in tables[0]['columns']):
                raise InventoryError('UNKNOWN_LINK_COLUMN', 'Link must reference existing columns.')
            selected.append((table_name, column_name))
        fingerprint = (first, *selected[0], last, *selected[1])
        if fingerprint in fingerprints:
            raise InventoryError('DUPLICATE_LINK', 'Duplicate cross-database link.')
        fingerprints.add(fingerprint)
        valid.append({
            'from_db_id': start['db_id'], 'from_db_label': start['label'],
            'from_table': selected[0][0], 'from_column': selected[0][1],
            'to_db_id': end['db_id'], 'to_db_label': end['label'],
            'to_table': selected[1][0], 'to_column': selected[1][1],
            'evidence': 'user_declared_unverified', 'verified': False,
        })
    result = dict(workspace)
    result['declared_cross_database_links'] = valid
    result['declared_cross_database_count'] = len(valid)
    # Never upgrade manually declared intent to verified FK evidence.
    result['cross_database_edges_verified'] = 0
    return result

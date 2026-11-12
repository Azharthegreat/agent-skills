"""Selective persisted desktop dependencies. Does not write source or destination state."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import tomllib
from urllib.parse import unquote

DB_TABLES = {
    'sqlite/codex-dev.db': {'automations', 'automation_runs', 'inbox_items', 'thread_timeline_ledger'},
    'sqlite/codex-thread-summaries-dev.db': {'thread_turn_summaries'},
}
IDENTITY_FIELDS = {'account_id', 'user_id', 'installation_id', 'host_id', 'host_key',
                   'principal_key', 'principal_id', 'environment_id'}
MAP_KEYS = {'thread-project-assignments', 'thread-writable-roots', 'queued-follow-ups',
            'thread-descriptions-v1', 'composer-prompt-drafts-v1', 'composer-prompt-drafts-v2',
            'client-thread-bindings-v1', 'unread-thread-ids-by-host-v1', 'prompt-history'}
LIST_KEYS = {'pinned-thread-ids', 'projectless-thread-ids'}
PREFIXES = ('thread-client-id-v1:', 'thread-tab-routes-v1:', 'thread-workspace-state-v1:')
FORBIDDEN_GLOBAL = ('permission', 'capability', 'grant', 'credential', 'token', 'auth')
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
SECRET = re.compile(r'(^\.env($|\.)|^auth\.json$|^credentials|^client_secret|^service.account|^id_(rsa|ed25519)|\.(pem|p12|pfx|jks|keystore|key)$|^(local|keystore)\.properties$|^google-services\.json$)',re.I)


def _links(value, ids):
    """Exact UUID membership, including URL-encoded UI keys; no prompt substring guesses."""
    if isinstance(value, str):
        return bool(set(UUID.findall(unquote(value).lower())) & ids)
    if isinstance(value, dict):
        return any(_links(k, ids) or _links(v, ids) for k, v in value.items())
    if isinstance(value, list):
        return any(_links(v, ids) for v in value)
    return False


def _slice(value, ids):
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            if _links(k, ids):
                result[k] = v
            elif _links(v, ids):
                # Binding objects belong as a unit; containers are filtered recursively.
                if isinstance(v, dict) and any(v.get(f) in ids for f in ('threadId', 'thread_id', 'id')):
                    result[k] = v
                elif isinstance(v, (dict, list)):
                    result[k] = _slice(v, ids)
                else:
                    result[k] = v
        return result
    if isinstance(value, list):
        return [v for v in value if _links(v, ids)]
    return value


def _read_db(path):
    c = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    return c


def _rows(c, table):
    # Table names are exclusively hard-coded constants.
    return [dict(r) for r in c.execute('SELECT * FROM "'+table+'"')]


def _file_tree(root, home, result):
    if not root.exists():
        return
    if root.is_symlink() or (hasattr(root, 'is_junction') and root.is_junction()) or not root.resolve().is_relative_to(home.resolve()):
        result['blockers'].append('Linked dependency root cannot be copied: '+str(root))
        return
    def fail(error):
        raise error
    for base, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        for name in list(dirs):
            p = Path(base)/name
            if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
                dirs.remove(name)
                result['blockers'].append('Linked dependency directory cannot be copied: '+str(p))
        for name in files:
            p = Path(base)/name
            if name.casefold() in {'claude.md','agents.md','agent.md','skill.md'}:
                continue
            if root == home/'memories' and not _links(str(p.relative_to(root)), set(result['session_ids'])):
                continue
            if SECRET.search(name):
                result['blockers'].append('Credential file excluded from dependency: '+str(p))
                continue
            if p.is_symlink() or not p.resolve().is_relative_to(home.resolve()):
                result['blockers'].append('Linked dependency file cannot be copied: '+str(p))
                continue
            kind = 'toml' if p.suffix.lower() == '.toml' else 'binary'
            try:
                p.read_text(encoding='utf-8')
                if kind != 'toml':
                    kind = 'text'
            except UnicodeError:
                pass
            result['files'].append({'source': str(p.resolve()), 'path': p.relative_to(home).as_posix(), 'kind': kind})


def _select_global(raw, ids, blockers):
    selected = {}
    for key, value in raw.items():
        if key == 'electron-persisted-atom-state' and isinstance(value, dict):
            nested = _select_global(value, ids, blockers)
            if nested:
                selected[key] = nested
        elif key in MAP_KEYS | LIST_KEYS:
            part = _slice(value, ids)
            if part:
                selected[key] = part
        elif key.startswith(PREFIXES) and _links(key, ids):
            selected[key] = value
        elif _links({key: value}, ids) and key not in {'sidebar-project-thread-orders'}:
            if any(word in key.lower() for word in FORBIDDEN_GLOBAL):
                blockers.append('Destination capability/permission setup required for selected state: '+key)
            else:
                blockers.append('Unsupported session-linked desktop state: '+key)
    assignments = selected.get('thread-project-assignments', {})
    project_ids = {v.get('projectId') for v in assignments.values() if isinstance(v, dict)} - {None}
    if project_ids:
        selected['local-projects'] = {k:v for k,v in raw.get('local-projects', {}).items() if k in project_ids}
        selected['project-order'] = [p for p in raw.get('project-order', []) if p in project_ids]
    orders = raw.get('sidebar-project-thread-orders', {})
    if isinstance(orders, dict):
        subset = {k:_slice(v, ids) for k,v in orders.items() if _links(v, ids)}
        if subset:
            selected['sidebar-project-thread-orders'] = subset
    # Drafts may be indexed by the client ID instead of the persisted thread ID.
    atoms = selected.get('electron-persisted-atom-state', {})
    source_atoms = raw.get('electron-persisted-atom-state', {})
    clients = {v for k,v in atoms.items() if k.startswith('thread-client-id-v1:') and isinstance(v, str)}
    clients |= set(atoms.get('client-thread-bindings-v1', {}))
    for key in ('composer-prompt-drafts-v1', 'composer-prompt-drafts-v2'):
        for client in clients:
            if client in source_atoms.get(key, {}):
                atoms.setdefault(key, {})[client] = source_atoms[key][client]
    return selected


def collect(home: Path, ids: set[str]) -> dict:
    home, ids = Path(home).resolve(), {i.lower() for i in ids}
    result = {'records': {}, 'files': [], 'global_state': {}, 'blockers': [], 'notes': [],
              'automation_ids': [], 'session_ids': sorted(ids), 'bindings': [],
              'source_timezone': {'names': list(time.tzname), 'utc_offset_seconds': -time.timezone}}
    dbrows = {}
    for rel, allowed in DB_TABLES.items():
        if not (home/rel).is_file():
            continue
        c = _read_db(home/rel)
        try:
            c.execute('BEGIN')
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            dbrows[rel] = {t:_rows(c, t) for t in allowed & tables}
        finally:
            c.close()
    desktop = dbrows.get('sqlite/codex-dev.db', {})
    automation_ids = {r['id'] for r in desktop.get('automations', []) if r.get('target_thread_id') in ids}
    automation_ids |= {r['automation_id'] for r in desktop.get('automation_runs', []) if r.get('thread_id') in ids}
    definitions = {}
    for path in sorted((home/'automations').glob('*/automation.toml')):
        try:
            definition = tomllib.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            result['blockers'].append('Unreadable automation definition prevents dependency discovery: '+str(path)+': '+str(exc))
            continue
        aid = definition.get('id', path.parent.name)
        if not isinstance(aid, str) or aid != path.parent.name:
            result['blockers'].append('Automation directory and definition identity disagree: '+str(path))
            continue
        definitions[aid] = definition
        if definition.get('target_thread_id') in ids:
            automation_ids.add(aid)
    result['automation_ids'] = sorted(automation_ids)
    for rel, table_rows in dbrows.items():
        selected = {}
        for table, rows in table_rows.items():
            matches = [r for r in rows if (r.get('id') in automation_ids if table == 'automations' else r.get('thread_id') in ids)]
            if matches:
                selected[table] = matches
                for r in matches:
                    for k in IDENTITY_FIELDS:
                        if r.get(k) is not None:
                            result['bindings'].append({'database': rel, 'table': table, 'field': k, 'source': r[k]})
        if selected:
            result['records'][rel] = selected
    by_id = {r['id']:r for r in desktop.get('automations', [])}
    behavior = {'name', 'prompt', 'status', 'rrule', 'kind', 'target_thread_id', 'notification_policy',
                'model', 'reasoning_effort', 'cwds', 'execution_environment', 'local_environment_config_path'}
    for aid in sorted(automation_ids):
        filedef, dbdef = definitions.get(aid), by_id.get(aid)
        if filedef is None or dbdef is None:
            result['blockers'].append('Automation '+aid+' is missing its '+('TOML' if filedef is None else 'database')+' representation; scheduler authority is unverified')
        if filedef is not None:
            _file_tree(home/'automations'/aid, home, result)
            for key in IDENTITY_FIELDS:
                if filedef.get(key) is not None:
                    result['bindings'].append({'file': 'automations/'+aid+'/automation.toml', 'field': key, 'source': filedef[key]})
        for rep in (filedef, dbdef):
            if rep and rep.get('target_thread_id') and rep['target_thread_id'] not in ids:
                result['blockers'].append('Automation '+aid+' requires target session '+rep['target_thread_id']+' outside selected closure')
        if filedef is not None and dbdef is not None:
            def equivalent(key):
                expected, actual = filedef[key], dbdef.get(key)
                if isinstance(expected,(list,dict)) and isinstance(actual,str):
                    try: actual=json.loads(actual)
                    except ValueError: pass
                return expected == actual
            mismatch = sorted(k for k in behavior if k in filedef and not equivalent(k))
            if mismatch:
                result['blockers'].append('Automation '+aid+' TOML/database behavior differs: '+', '.join(mismatch)+'; resolve scheduler authority on source')
    if automation_ids:
        result['notes'].append('Selected schedule statuses and next-run values are preserved. Scheduler registration, timezone interpretation and overdue/duplicate execution require destination runtime verification.')
    _file_tree(home/'memories', home, result)
    if (home/'memories').exists():
        result['notes'].append('Only memory files whose relative path identifies a selected session are included; unowned shared memory is outside session scope.')
    path = home/'.codex-global-state.json'
    if path.is_file():
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raise ValueError('Invalid source global state schema')
        result['global_state'] = _select_global(raw, ids, result['blockers'])
    setup=[b for b in result['blockers'] if b.startswith('Destination capability/permission setup required')]
    result['blockers']=[b for b in result['blockers'] if b not in setup]
    result['required_setup']=setup
    result['notes'].extend(setup)
    return result


def _merge(current, incoming):
    if isinstance(current, dict) and isinstance(incoming, dict):
        merged = copy.deepcopy(current)
        for key, value in incoming.items():
            merged[key] = _merge(merged[key], value) if key in merged else value
        return merged
    if isinstance(current, list) and isinstance(incoming, list):
        # Keep unrelated destination ordering; exact repeats are idempotent.
        return current + [v for v in incoming if v not in current]
    return incoming


def _conflicts(current, incoming, path='global_state'):
    result=[]
    if isinstance(current,dict) and isinstance(incoming,dict):
        for k,v in incoming.items():
            if k in current:
                result.extend(_conflicts(current[k],v,path+'/'+k))
    elif isinstance(current,list) and isinstance(incoming,list):
        pass  # Selected list membership is merged without removing other items.
    elif current != incoming:
        result.append('Existing selected desktop state differs: '+path)
    return result


def prepare(payload: dict, home: Path, mappings: list[tuple], mapper, identity_map: dict) -> dict:
    home = Path(home).resolve()
    blockers = list(payload.get('blockers', []))
    notes = list(payload.get('notes', []))
    identity_map = dict(identity_map or {})
    records = copy.deepcopy(payload.get('records', {}))
    for rel, data in records.items():
        if rel not in DB_TABLES or not set(data) <= DB_TABLES[rel]:
            raise ValueError('Unsupported supplemental database/table')
        for table, rows in data.items():
            for row in rows:
                for field in IDENTITY_FIELDS & row.keys():
                    value = row[field]
                    if value is None:
                        continue
                    replacement = identity_map.get(str(value))
                    if replacement is None:
                        blockers.append('Unresolved destination binding '+rel+'/'+table+'/'+field+' (provide explicit identity mapping)')
                    elif not isinstance(replacement, str) or not replacement:
                        raise ValueError('Identity mapping must have nonempty string destination')
                    else:
                        row[field] = replacement
    for binding in payload.get('bindings', []):
        if 'file' in binding and str(binding['source']) not in identity_map:
            blockers.append('Unresolved destination binding in '+binding['file']+'/'+binding['field'])
    if payload.get('automation_ids'):
        source_tz = payload.get('source_timezone')
        local_tz = {'names': list(time.tzname), 'utc_offset_seconds': -time.timezone}
        if source_tz != local_tz:
            blockers.append('Source/destination scheduler timezone differs or is missing; verify recurrence translation before import')
    records = mapper(records, mappings)
    incoming = copy.deepcopy(payload.get('global_state', {}))
    def validate_global(data, nested=False):
        if not isinstance(data, dict):
            raise ValueError('Invalid supplemental global-state schema')
        for key, value in data.items():
            if key == 'electron-persisted-atom-state' and not nested:
                validate_global(value, True)
            elif key in MAP_KEYS | LIST_KEYS | {'local-projects', 'project-order', 'sidebar-project-thread-orders'}:
                if not isinstance(value, (dict, list)):
                    raise ValueError('Invalid selected global-state container: '+key)
            elif key.startswith(PREFIXES):
                if not _links(key, set(payload.get('session_ids', []))):
                    raise ValueError('Unrelated global-state key in archive')
            else:
                raise ValueError('Unapproved global-state key in archive: '+key)
    validate_global(incoming)
    validation_blockers = []
    scoped = _select_global(incoming, set(payload.get('session_ids', [])), validation_blockers)
    if scoped != incoming or validation_blockers:
        raise ValueError('Unrelated or unsupported entries in supplemental global state')
    # Apply path mapping to dictionary keys too; UI host and workspace keys contain paths.
    def remap(value):
        if isinstance(value, dict):
            result = {}
            for k,v in value.items():
                key = identity_map.get(k, mapper(k, mappings))
                if key in result:
                    raise ValueError('Global state path/identity mapping collision')
                result[key] = remap(v)
            return result
        if isinstance(value, list):
            return [remap(v) for v in value]
        if isinstance(value, str) and value in identity_map:
            return identity_map[value]
        return mapper(value, mappings)
    incoming = remap(incoming)
    files = []
    conflicts = []
    if incoming:
        target = home/'.codex-global-state.json'
        current = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
        if not isinstance(current, dict):
            raise ValueError('Invalid destination global state schema')
        merged = _merge(current, incoming)
        conflicts = _conflicts(current,incoming)
        files.append({'target': str(target), 'data': json.dumps(merged, ensure_ascii=False, indent=2)+'\n'})
    return {'records': records, 'files': files, 'blockers': sorted(set(blockers)), 'notes': notes, 'conflicts': conflicts}

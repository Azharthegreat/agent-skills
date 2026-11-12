#!/usr/bin/env python3
"""Portable Codex session archives. Standard library only; transport is skill-owned."""
import argparse
import csv
from contextlib import contextmanager, ExitStack
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

FORMAT = 2
INSTRUCTION_FILES = {'claude.md','agents.md','agent.md','skill.md'}
_ISOLATED_HOMES = set()
ASSETS = {'attachments', 'generated_images', 'visualizations', 'memories', 'automations'}
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', '.gradle',
             '.next', '.codex', 'secrets', '.ssh', '.aws'}
SECRET = re.compile(r'(^\.env($|\.)|^auth\.json$|^credentials|^client_secret|'
                    r'^service.account|^id_(rsa|ed25519)|\.(pem|p12|pfx|jks|keystore|key)$|'
                    r'^(local|keystore)\.properties$|^google-services\.json$)', re.I)
DB_NAMES = re.compile(r'^(state|thread_history|goals|memories|queue)_\d+\.sqlite$')
TABLES = {'threads', 'thread_dynamic_tools', 'thread_spawn_edges', 'thread_artifacts',
          'projects', 'project_roots', 'thread_sections', 'thread_turns', 'thread_items',
          'thread_history_projection_state', 'thread_realtime_items', 'stage1_outputs',
          'thread_goals', 'thread_goal_continuation_deferrals', 'queued_items', 'queued_thread_revisions'}


def fs_path(value):
    text = str(value)
    if text.startswith('\\\\?\\UNC\\'):
        text = '\\\\'+text[8:]
    elif text.startswith('\\\\?\\'):
        text = text[4:]
    return Path(text).resolve()


def home_path(value=None):
    return fs_path(value or os.environ.get('CODEX_HOME') or Path.home()/'.codex')


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def ident(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', value):
        raise ValueError('Invalid SQL identifier')
    return '"'+value+'"'


@contextmanager
def ro_db(path):
    c = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


@contextmanager
def rw_db(path):
    c = sqlite3.connect(path)
    try:
        with c:
            yield c
    finally:
        c.close()


def tables(c):
    return [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\'")]


def columns(c, table):
    return {r['name']: dict(r) for r in c.execute('PRAGMA table_info('+ident(table)+')')}


def selected(c, table, col, values):
    if not values:
        return []
    result = []
    vals = sorted(values)
    for i in range(0, len(vals), 500):
        batch = vals[i:i+500]
        result.extend(dict(r) for r in c.execute('SELECT * FROM '+ident(table)+' WHERE '+ident(col)+' IN ('+','.join('?'*len(batch))+')', batch))
    return result


def safe_rel(name):
    p = PurePosixPath(name)
    if not name or '\\' in name or p.is_absolute() or any(x in ('..', '.') for x in name.split('/')):
        raise ValueError('Unsafe archive path: '+name)
    for part in p.parts:
        if not part or ':' in part or part.endswith((' ', '.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?', part):
            raise ValueError('Nonportable archive path: '+name)
    return p


def contained(root, rel):
    p = root.joinpath(*safe_rel(rel).parts)
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('Destination escapes root: '+str(p))
    # Refuse links and Windows junctions, even if they happen to point inside root.
    for q in [p, *p.parents]:
        if q == root.parent:
            break
        if q.is_symlink() or (hasattr(q, 'is_junction') and q.is_junction()):
            raise ValueError('Link/junction in destination: '+str(q))
    return p


def walk_files(root, excluded):
    def fail(error):
        raise error
    for base, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        parent = Path(base)
        for name in list(dirs):
            p = parent/name
            if name.casefold() in SKIP_DIRS or p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
                dirs.remove(name)
                excluded.append({'path': str(p), 'reason': 'excluded directory or link'})
        for name in files:
            p = parent/name
            if p.is_symlink() or SECRET.search(name) or name.casefold() in INSTRUCTION_FILES:
                excluded.append({'path': str(p), 'reason': 'credential filename or link'})
            else:
                yield p


def strings(obj):
    if isinstance(obj, str):
        yield obj
        if obj[:1] in ('{', '['):
            try:
                yield from strings(json.loads(obj))
            except (ValueError, RecursionError):
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def normalized(s):
    return s.replace('\\\\', '\\').replace('\\', '/').casefold()


def referenced_paths(corpus, root):
    """Index path prefixes once instead of scanning a large transcript per disk file."""
    prefix = normalized(str(root)).rstrip('/')
    result = set()
    for match in re.finditer(re.escape(prefix)+r'/[^\n\r\"<>|?*]+', corpus):
        value = match.group().rstrip()
        result.add(value.rstrip("'.,);]}"))
        for boundary in re.finditer(r"[\s'(),;\]}]", value):
            result.add(value[:boundary.start()].rstrip('.'))
    return result


def map_value(obj, mappings):
    if isinstance(obj, dict):
        return {k: map_value(v, mappings) for k, v in obj.items()}
    if isinstance(obj, list):
        return [map_value(v, mappings) for v in obj]
    if not isinstance(obj, str):
        return obj
    if obj[:1] in ('{', '['):
        try:
            return dumps(map_value(json.loads(obj), mappings)).decode('utf-8')
        except ValueError:
            pass
    # One pass prevents cascading when destination is under an old source root.
    variants = {}
    for old, new in sorted(mappings, key=lambda x: len(x[0]), reverse=True):
        for source, dest in [(old, new), (old.replace('\\', '/'), new.replace('\\', '/')),
                             (old.replace('\\', '\\\\'), new.replace('\\', '\\\\'))]:
            variants.setdefault(source.rstrip('/\\').casefold(), dest.rstrip('/\\'))
    if not variants:
        return obj
    pattern = '|'.join(re.escape(x) for x in sorted(variants, key=len, reverse=True))
    by_case = {k.casefold(): v for k, v in variants.items()}
    def replace(match):
        prefix, suffix = match.group('prefix'), match.group('suffix') or ''
        dest = by_case[prefix.casefold()]
        if dest.startswith('/'):
            suffix = suffix.replace('\\\\', '/').replace('\\', '/')
        elif re.match(r'^[A-Za-z]:', dest):
            suffix = suffix.replace('/', '\\')
        return dest+suffix
    return re.sub(r'(?<![\w])(?P<prefix>'+pattern+r')(?=$|[/\\\s\"\'<>),:;\]])(?P<suffix>(?:[/\\][^\s\"\'<>|),;]*)?)',
                  replace, obj, flags=re.I)


def dependency_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location('session_dependencies', Path(__file__).with_name('session_dependencies.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def allowed_database(name):
    return bool(DB_NAMES.fullmatch(name)) or name in {'sqlite/codex-dev.db', 'sqlite/codex-thread-summaries-dev.db'}


@contextmanager
def import_lock(home, enabled):
    if not enabled:
        yield
        return
    folder = contained(home, 'session-transfer')
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder/'import.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Another import or interrupted import holds '+str(lock))
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(dumps({'pid': os.getpid(), 'created': time.time()}))
        yield
    finally:
        lock.unlink(missing_ok=True)


def journal_write(path, data):
    temp = path.with_suffix('.tmp')
    with temp.open('wb') as stream:
        stream.write(dumps(data))
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def db_fingerprint(path):
    with ro_db(path) as c:
        return sha('\n'.join(c.iterdump()).encode('utf-8'))


def upsert_rows(c, table, rows, conflicts):
    cols = columns(c, table)
    pks = [k for k,v in sorted(cols.items(), key=lambda x: x[1]['pk']) if v['pk']]
    if not pks:
        raise ValueError('Table has no supported primary key: '+table)
    for row in rows:
        if set(row)-cols.keys() or not set(pks) <= row.keys():
            raise ValueError('Incompatible columns/key for '+table)
        where = ' AND '.join(ident(k)+'=?' for k in pks)
        old = c.execute('SELECT * FROM '+ident(table)+' WHERE '+where, [row[k] for k in pks]).fetchone()
        if old is not None:
            old = dict(old)
            if any(old[k] != v for k,v in row.items()):
                conflicts.append('Existing row differs: '+table)
                changed = [k for k in row if k not in pks]
                if changed:
                    c.execute('UPDATE '+ident(table)+' SET '+','.join(ident(k)+'=?' for k in changed)+' WHERE '+where,
                              [row[k] for k in changed]+[row[k] for k in pks])
        else:
            keys = list(row)
            c.execute('INSERT INTO '+ident(table)+' ('+','.join(map(ident,keys))+') VALUES ('+','.join('?'*len(keys))+')',[row[k] for k in keys])


def export_session(args):
    sid = str(uuid.UUID(args.session_id))
    h = home_path(args.codex_home)
    dbs = sorted(p for p in h.glob('*.sqlite') if DB_NAMES.fullmatch(p.name))
    states = [p for p in dbs if p.name.startswith('state_')]
    if len(states) != 1:
        raise ValueError('Expected one active state database; inspect Codex version/layout first')
    excluded, entries, stable, frozen_rollouts = [], [], {}, {}
    with tempfile.TemporaryDirectory(prefix='codex-session-export-') as tmp:
        tmp = Path(tmp)
        snapshots = {}
        for db in dbs:
            snap = tmp/db.name
            with ro_db(db) as source, rw_db(snap) as dest:
                source.backup(dest)
            snapshots[db.name] = snap
        with ro_db(snapshots[states[0].name]) as c:
            ts = {r['id']: dict(r) for r in c.execute('SELECT * FROM threads')}
            if sid not in ts:
                raise ValueError('Session ID is not present in the source state database')
            ids = {sid}
            edges = [dict(r) for r in c.execute('SELECT * FROM thread_spawn_edges')] if 'thread_spawn_edges' in tables(c) else []
            relationships = []
            for thread_id, row in ts.items():
                candidate = Path(row['rollout_path'])
                if not candidate.is_file():
                    continue
                try:
                    with candidate.open(encoding='utf-8') as stream:
                        meta = json.loads(stream.readline()).get('payload', {})
                    parents = {meta.get('parent_thread_id'), meta.get('forked_from_id'),
                               (meta.get('history_base') or {}).get('thread_id')}
                    source = meta.get('source')
                    if isinstance(source, dict):
                        parents.add(source.get('subagent', {}).get('thread_spawn', {}).get('parent_thread_id'))
                    relationships.extend((parent,thread_id) for parent in parents if parent)
                except (ValueError, AttributeError):
                    if thread_id == sid:
                        raise ValueError('Invalid selected rollout metadata')
            relationships.extend((r['parent_thread_id'],r['child_thread_id']) for r in edges)
            if not args.single:
                while True:
                    more = {child for parent,child in relationships if parent in ids}
                    if more <= ids:
                        break
                    ids |= more
                while True:
                    ancestors = {parent for parent,child in relationships if child in ids}
                    if ancestors <= ids:
                        break
                    ids |= ancestors
            if not ids <= ts.keys():
                raise ValueError('Missing child thread records')
        root = fs_path(args.project_root or ts[sid]['cwd'])
        if root == root.parent or root == Path.home().resolve() or root == h:
            raise ValueError('Supply a concrete project path for metadata mapping')
        if not fs_path(ts[sid]['cwd']).is_relative_to(root):
            raise ValueError('Project root must contain session cwd')
        records = {}
        for name, snap in snapshots.items():
            with ro_db(snap) as c:
                data = {}
                for table in tables(c):
                    if table not in TABLES:
                        continue
                    cols = columns(c, table)
                    rows = []
                    if table == 'threads':
                        rows = selected(c, table, 'id', ids)
                    elif table == 'thread_spawn_edges':
                        rows = [r for r in edges if r['parent_thread_id'] in ids and r['child_thread_id'] in ids]
                    elif 'thread_id' in cols:
                        rows = selected(c, table, 'thread_id', ids)
                    elif table in ('projects', 'project_roots', 'thread_sections'):
                        fk = 'thread_section_id' if table == 'thread_sections' else 'project_id'
                        values = {ts[i].get(fk) for i in ids} - {None}
                        rows = selected(c, table, 'project_id' if table == 'project_roots' else 'id', values)
                    if rows:
                        data[table] = rows
                if data:
                    records[name] = data
        for i in ids:
            if ts[i].get('history_mode') == 'paginated':
                history = [data for name,data in records.items() if name.startswith('thread_history_')]
                if not history or not any(any(r.get('thread_id') == i for r in data.get('thread_history_projection_state',[])) for data in history):
                    raise ValueError('Missing paginated history/projection for '+i)
        supplemental = dependency_module().collect(h, ids)
        for name, data in supplemental.get('records', {}).items():
            records[name] = data
        corpus_parts = list(strings(records))
        rollouts = {}
        def add_file(path, area, rel, kind='binary'):
            path = path.resolve()
            if path.name.casefold() in INSTRUCTION_FILES:
                raise ValueError('Instruction files are not session payloads: '+str(path))
            if SECRET.search(path.name):
                raise ValueError('Credential filename cannot be exported as a dependency: '+str(path))
            if not path.is_file():
                raise ValueError('Missing dependency: '+str(path))
            if path in stable:
                return next(e for e in entries if e['source'] == str(path))
            st = path.stat()
            stable[path] = (st.st_size, st.st_mtime_ns)
            arc = 'files/'+area+'/'+safe_rel(rel).as_posix()
            entries.append({'archive': arc, 'area': area, 'path': rel, 'source': str(path), 'kind': kind})
            return entries[-1]
        for i in sorted(ids):
            p = Path(ts[i]['rollout_path']).resolve()
            if not p.is_relative_to(h) or p.relative_to(h).parts[0] not in {'sessions', 'archived_sessions'}:
                raise ValueError('Rollout lies outside the active Codex home')
            raw = p.read_bytes()
            if not raw.endswith(b'\n'):
                raise ValueError('Incomplete active rollout; retry when session is idle')
            rows = [json.loads(line) for line in raw.splitlines()]
            meta = rows[0].get('payload', {})
            if i not in (meta.get('id'), meta.get('session_id')):
                raise ValueError('Rollout ID mismatch')
            parent = meta.get('parent_thread_id') or meta.get('forked_from_id')
            if parent and parent not in ids:
                excluded.append({'path': str(parent), 'reason': 'external parent/fork; export separately if inherited history is incomplete'})
            corpus_parts.extend(strings(rows))
            rel = p.relative_to(h).as_posix()
            rollouts[i] = rel
            add_file(p, 'codex', rel, 'rollout')
            if getattr(args,'live_snapshot',False):
                frozen_rollouts[p] = raw
        corpus = normalized('\n'.join(corpus_parts))
        print('Export: history collected; indexing file references', file=sys.stderr)
        codex_references = referenced_paths(corpus, h)
        relative_asset_references = set()
        for bucket in ('attachments','generated_images','visualizations'):
            relative_asset_references.update(referenced_paths(corpus,bucket))
        print('Export: collecting session assets', file=sys.stderr)
        for bucket in {'attachments', 'generated_images', 'visualizations'}:
            if not (h/bucket).exists():
                continue
            for p in walk_files(h/bucket, excluded):
                rel = p.relative_to(h).as_posix()
                if any(i in str(p) for i in ids) or normalized(str(p)) in codex_references or normalized(rel) in relative_asset_references:
                    add_file(p, 'codex', rel)
        for item in supplemental.get('files', []):
            add_file(Path(item['source']), 'codex', item['path'], item.get('kind','binary'))
        # Session exports do not enumerate or copy workspace/skill directories.
        extra_maps = []
        for index, value in enumerate(args.include or []):
            original = Path(value)
            if original.is_symlink() or (hasattr(original,'is_junction') and original.is_junction()):
                raise ValueError('Extra dependency is a link/junction')
            p = original.resolve()
            if SECRET.search(p.name) or p.name.casefold() in INSTRUCTION_FILES:
                raise ValueError('Instruction or credential files are not session attachments')
            if p.is_dir():
                raise ValueError('--include accepts a specific session attachment file, not a directory')
            candidates = [p]
            for child in candidates:
                if child.resolve() in stable:
                    continue
                if child.is_relative_to(root):
                    add_file(child,'project',child.relative_to(root).as_posix())
                else:
                    tail = child.relative_to(p).as_posix() if p.is_dir() else p.name
                    rel = f'attachments/session-transfer/{sid}/{index}/{tail}'
                    add_file(child, 'codex', rel)
                    extra_maps.append([str(child), rel])
        missing = sorted(set(re.findall(r'(?<![A-Za-z0-9/])(?:[A-Za-z]:[/\\]|/)[^\s<>"|?*]{1,4096}[.](?:png|jpg|jpeg|webp|gif|pdf|docx|pptx|xlsx|csv|mp3|mp4)', '\n'.join(corpus_parts))))
        known = {normalized(e['source']) for e in entries}
        unresolved = [p for p in missing if normalized(p) not in known and not p.startswith(('//', '/api/'))]
        total = sum(x[0] for x in stable.values())
        print('Export: writing '+str(len(entries))+' files', file=sys.stderr)
        if total > args.max_bytes:
            raise ValueError(f'Archive input size {total} exceeds --max-bytes; choose a narrower project root or raise the limit')
        outdir = Path(args.folder or h/'session-transfer'/'staging').resolve()
        if outdir.is_relative_to(root) and args.project_mode == 'snapshot':
            raise ValueError('Export folder must be outside project snapshot root')
        outdir.mkdir(parents=True, exist_ok=True)
        output = outdir/(sid+'.zip')
        if output.exists():
            raise ValueError('Archive already exists; choose a version subfolder to preserve it')
        manifest = {'format': FORMAT, 'session_id': sid, 'session_ids': sorted(ids),
                    'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'source_codex_home': str(h), 'source_project_root': str(root),
                    'source_codex_alias': str(Path(args.codex_home or h)),
                    'source_project_alias': str(Path(ts[sid]['cwd'])) if fs_path(ts[sid]['cwd']) == root else str(Path(args.project_root or root)),
                    'source_user_home': str(Path.home()), 'project_mode': 'none',
                    'rollouts': rollouts, 'extra_maps': extra_maps,
                    'excluded': excluded, 'unresolved_references': unresolved,
                    'limitations': ['Snapshot of persisted local data only; no live processes, remote blobs, credentials or hidden server state.',
                                    'Project trees, instruction files, other skills/plugins and unowned shared memory are not session payloads.'],
                    'files': entries, 'supplemental': supplemental,
                    'completeness': {'blockers': supplemental.get('blockers', []),
                                     'notes': supplemental.get('notes', []),
                                     'project_mode': 'none'}}
        if frozen_rollouts:
            manifest['capture_mode'] = 'live persisted snapshot'
            manifest['limitations'].append('Active export freezes each SQLite snapshot and rollout prefix during capture. Later messages and updates are outside this backup; stores are not one atomic application transaction.')
        defaults = Path(__file__).resolve().parent.parent/'assets'/'defaults.json'
        if defaults.is_file():
            manifest['drive'] = json.loads(defaults.read_text(encoding='utf-8'))
        work = output.with_suffix('.zip.partial')
        try:
            with zipfile.ZipFile(work, 'x', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as z:
                for e in entries:
                    data = frozen_rollouts.get(Path(e['source']))
                    if data is None: data = Path(e['source']).read_bytes()
                    e['size'], e['sha256'] = len(data), sha(data)
                    z.writestr(e['archive'], data)
                data = dumps(records)
                manifest['records_sha256'] = sha(data)
                z.writestr('records.json', data)
                # Session-scoped JSONL indices; never ship the global index/history wholesale.
                indices = {}
                for name in ('session_index.jsonl', 'history.jsonl'):
                    if (h/name).exists():
                        indices[name] = [r for line in (h/name).read_text(encoding='utf-8').splitlines()
                                         if line.strip() and (r := json.loads(line)).get('id', r.get('session_id')) in ids]
                data = dumps(indices)
                manifest['indices_sha256'] = sha(data)
                z.writestr('indices.json', data)
                z.writestr('manifest.json', dumps(manifest))
            for p, sig in stable.items():
                if p in frozen_rollouts:
                    with p.open('rb') as source:
                        if source.read(len(frozen_rollouts[p])) != frozen_rollouts[p]:
                            raise ValueError('Captured rollout prefix was modified during export')
                    continue
                st = p.stat()
                if sig != (st.st_size, st.st_mtime_ns):
                    raise ValueError('Source changed during export; retry when idle: '+str(p))
            # Detect commits to any selected DB after its snapshot, without modifying the source.
            for name, snap in snapshots.items():
                with ro_db(h/name) as live, ro_db(snap) as old:
                    for table, rows in records.get(name, {}).items():
                        cols = columns(old, table)
                        col = 'thread_id' if 'thread_id' in cols else ('id' if table == 'threads' else None)
                        if col and not frozen_rollouts and selected(live, table, col, ids) != selected(old, table, col, ids):
                            raise ValueError('Session database changed during export; retry when idle')
            if dependency_module().collect(h, ids) != supplemental:
                raise ValueError('Session dependencies changed during export; retry when idle')
            with zipfile.ZipFile(work) as check:
                if sum(e.file_size for e in check.infolist()) > args.max_bytes:
                    raise ValueError('Complete archive including metadata exceeds --max-bytes')
            work.replace(output)
        finally:
            if work.exists():
                work.unlink()
    return {'zip': str(output), 'sha256': file_sha(output), 'session_count': len(ids),
            'file_count': len(entries), 'excluded_count': len(excluded), 'unresolved_references': unresolved,
            'transport': 'local archive prepared; Drive upload is a separate browser step'}


def read_bundle(path, max_bytes):
    z = zipfile.ZipFile(path)
    try:
        seen = set()
        total = 0
        for e in z.infolist():
            safe_rel(e.filename)
            if e.filename.casefold() in seen or stat.S_ISLNK(e.external_attr >> 16) or e.flag_bits & 1:
                raise ValueError('Duplicate, encrypted or symlink ZIP entry')
            seen.add(e.filename.casefold())
            total += e.file_size
        if total > max_bytes or len(seen) > 200000:
            raise ValueError('Archive exceeds size/file limit')
        if z.getinfo('manifest.json').file_size > 32*1024*1024:
            raise ValueError('Manifest too large')
        m = json.loads(z.read('manifest.json'))
        if m.get('format') not in {1, FORMAT}:
            raise ValueError('Unsupported archive format')
        sid = str(uuid.UUID(m['session_id']))
        ids = {str(uuid.UUID(i)) for i in m['session_ids']}
        if sid not in ids or set(m['rollouts']) != ids:
            raise ValueError('Invalid session membership')
        expected = {'manifest.json', 'records.json', 'indices.json'}
        destinations = set()
        for e in m['files']:
            rel = safe_rel(e['path'])
            if rel.name.casefold() in INSTRUCTION_FILES:
                raise ValueError('Instruction files are outside the session archive scope')
            if e['area'] not in {'codex', 'project'} or e['archive'] != f"files/{e['area']}/{rel.as_posix()}":
                raise ValueError('Invalid file routing')
            if e['area'] == 'codex' and rel.parts[0] not in ASSETS | {'sessions', 'archived_sessions'}:
                raise ValueError('Archive attempts to change protected Codex state')
            if e['area'] == 'codex' and rel.parts[0] in {'sessions','archived_sessions'}:
                if e['kind'] != 'rollout' or rel.as_posix() not in m['rollouts'].values():
                    raise ValueError('Unrelated or unvalidated rollout file')
            if e['kind'] == 'rollout' and (e['area'] != 'codex' or rel.as_posix() not in m['rollouts'].values()):
                raise ValueError('Invalid rollout routing')
            key = (e['area'], str(rel).casefold())
            if key in destinations or e['archive'] in expected:
                raise ValueError('Duplicate manifest destination')
            destinations.add(key)
            expected.add(e['archive'])
            if z.getinfo(e['archive']).file_size != e['size']:
                raise ValueError('File size mismatch')
            with z.open(e['archive']) as f:
                if hashlib.file_digest(f, 'sha256').hexdigest() != e['sha256']:
                    raise ValueError('File checksum mismatch')
        if {e.filename for e in z.infolist()} != expected:
            raise ValueError('Unlisted ZIP entries')
        for name in ('records', 'indices'):
            if sha(z.read(name+'.json')) != m[name+'_sha256']:
                raise ValueError('Metadata checksum mismatch')
        records, indices = json.loads(z.read('records.json')), json.loads(z.read('indices.json'))
        state_sets = [d.get('threads', []) for n, d in records.items() if n.startswith('state_')]
        if len(state_sets) != 1 or {r.get('id') for r in state_sets[0]} != ids:
            raise ValueError('Missing or inconsistent thread metadata')
        for name, data in records.items():
            if not allowed_database(name):
                raise ValueError('Unapproved database target')
            for table, rows in data.items():
                ident(table)
                if table not in TABLES and table not in getattr(dependency_module(),'DB_TABLES',{}).get(name,set()):
                    raise ValueError('Unapproved table in archive')
                for r in rows:
                    if table == 'threads':
                        valid = r.get('id') in ids
                    elif table == 'thread_spawn_edges':
                        valid = r.get('parent_thread_id') in ids and r.get('child_thread_id') in ids
                    elif table in {'projects', 'project_roots', 'thread_sections'}:
                        valid = True  # Export evidence only; destination project identity is selected locally.
                    elif name.startswith('sqlite/'):
                        valid = True  # Validated against supplemental relationships below.
                    else:
                        valid = r.get('thread_id') in ids
                    if not valid:
                        raise ValueError('Unrelated database row in archive')
        extra_records = m.get('supplemental',{}).get('records',{})
        if {n:d for n,d in records.items() if n.startswith('sqlite/')} != extra_records:
            raise ValueError('Supplemental database manifest mismatch')
        automation_ids = set(m.get('supplemental',{}).get('automation_ids',[]))
        for name,data in extra_records.items():
            for table,rows in data.items():
                for row in rows:
                    if table=='automations':
                        if row.get('id') not in automation_ids:
                            raise ValueError('Unrelated automation row')
                    elif row.get('thread_id') not in ids:
                        raise ValueError('Unrelated supplemental session row')
        for entry in m['files']:
            if entry['area']=='codex' and entry['path'].startswith('automations/'):
                if PurePosixPath(entry['path']).parts[1] not in automation_ids:
                    raise ValueError('Unrelated automation file')
        validate = getattr(dependency_module(), 'validate', None)
        if validate:
            validate(m.get('supplemental',{}), ids)
        return z, m, records, indices
    except BaseException:
        z.close()
        raise


def no_codex_processes():
    if os.name == 'nt':
        result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, check=True)
        names = [r[0].lower() for r in csv.reader(io.StringIO(result.stdout)) if r]
        running = [n for n in names if re.fullmatch(r'codex(?:-app-server)?\.exe', n)]
    else:
        result = subprocess.run(['ps', '-A', '-o', 'comm='], capture_output=True, text=True, check=True)
        running = [n for n in result.stdout.splitlines() if Path(n.strip()).name.lower() in {'codex', 'codex-app-server', 'codex app'}]
    if running:
        raise ValueError('Close Codex desktop, CLI, IDE sessions and app servers before applying import')


@contextmanager
def isolated_destination(parent, schema_home):
    """Allocate a fresh private test home using trusted LOCAL runtime schemas only.

    No server may be launched against this home until this context exits.
    The exemption cannot be selected by import CLI or an archive.
    """
    parent = Path(parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix='restored-', dir=parent)).resolve()
    source_home = home_path(schema_home)
    names = [p.name for p in source_home.glob('*.sqlite') if DB_NAMES.fullmatch(p.name)]
    names += [n for n in dependency_module().DB_TABLES if (source_home/n).is_file()]
    for name in names:
        target = home/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with ro_db(source_home/name) as source, rw_db(target) as dest:
            schema = list(source.execute("SELECT type,sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END"))
            for row in schema:
                dest.execute(row['sql'])
            for row in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%migration%' OR name='_sqlx_migrations')"):
                table = row['name']
                for data in source.execute('SELECT * FROM '+ident(table)):
                    dest.execute('INSERT INTO '+ident(table)+' VALUES ('+','.join('?'*len(data))+')',tuple(data))
            for pragma in ('user_version','application_id'):
                dest.execute('PRAGMA '+pragma+'='+str(source.execute('PRAGMA '+pragma).fetchone()[0]))
    _ISOLATED_HOMES.add(home)
    try:
        yield home
    finally:
        _ISOLATED_HOMES.discard(home)


def destination_offline(home):
    if home not in _ISOLATED_HOMES:
        no_codex_processes()


def import_session(args):
    h = home_path(args.codex_home)
    with import_lock(h, args.apply):
        return _import_session(args, h)


def _import_session(args, h):
    root = Path(args.project_root).resolve()
    if root == root.parent or root == Path.home().resolve() or root == h or root.is_relative_to(h) or h.is_relative_to(root):
        raise ValueError('Choose a project folder separate from Codex home')
    if args.apply:
        if not args.offline_confirmed:
            raise ValueError('--offline-confirmed is required after closing Codex')
        destination_offline(h)
        for journal in (h/'session-transfer'/'backups').glob('*/journal.json'):
            if json.loads(journal.read_text(encoding='utf-8')).get('status') in {'applying','committing','recovery_required'}:
                raise ValueError('An interrupted import needs recovery first: '+str(journal))
    z, m, records, indices = read_bundle(Path(args.zip), args.max_bytes)
    with z, tempfile.TemporaryDirectory(prefix='codex-session-import-') as tmp:
        tmp = Path(tmp)
        sid, ids = m['session_id'], set(m['session_ids'])
        if args.session_id and str(uuid.UUID(args.session_id)) != sid:
            raise ValueError('Requested session ID does not match archive')
        mappings = []
        for item in args.map or []:
            old, new = item.split('=', 1)
            mappings.append((old, str(Path(new).resolve())))
        mappings.extend([(m['source_codex_home'], str(h)), (m['source_project_root'], str(root)),
                         (m.get('source_codex_alias', m['source_codex_home']), str(h)),
                         (m.get('source_project_alias', m['source_project_root']), str(root))])
        for source, rel in m.get('extra_maps', []):
            mappings.insert(0, (source, str(contained(h, rel))))
        identity_map = {}
        for value in getattr(args,'identity_map',[]) or []:
            old,new = value.split('=',1)
            identity_map[old] = new
        supplemental = dependency_module().prepare(m.get('supplemental',{}), h, mappings, map_value, identity_map)
        blockers = supplemental.get('blockers',[])
        if blockers and not getattr(args,'allow_incomplete',False):
            raise ValueError('Full restoration blocked: '+'; '.join(blockers))
        records.update(supplemental.get('records',{}))
        file_plans, offsets = [], {}
        def plan_file(target, data, area):
            target = Path(target)
            if target.exists() and not target.is_file():
                raise ValueError('Destination file collides with a directory: '+str(target))
            before = file_sha(target) if target.exists() else None
            checksum = sha(data)
            staged = tmp/('file-'+str(len(file_plans)))
            staged.write_bytes(data)
            file_plans.append({'target':target,'staged':staged,'before':before,'sha256':checksum,
                               'conflict':before is not None and before != checksum,'area':area})
        for e in m['files']:
            target = contained(h if e['area'] == 'codex' else root, e['path'])
            data = z.read(e['archive'])
            if e['kind'] == 'rollout':
                thread_id = next(i for i, rel in m['rollouts'].items() if rel == e['path'])
                first = json.loads(data.splitlines()[0])
                if first.get('type') != 'session_meta' or thread_id not in (first.get('payload', {}).get('id'), first.get('payload', {}).get('session_id')):
                    raise ValueError('Imported rollout ID mismatch')
                oldpos = newpos = 0
                offset_map = {0: 0}
                lines = []
                for line in data.splitlines(keepends=True):
                    row = map_value(json.loads(line), mappings)
                    new = dumps(row)+b'\n'
                    lines.append(new)
                    oldpos += len(line)
                    newpos += len(new)
                    offset_map[oldpos] = newpos
                data = b''.join(lines)
                offsets[thread_id] = offset_map
            elif e['kind'] in {'text','toml'}:
                data = map_value(data.decode('utf-8'), mappings).encode('utf-8')
                if e['kind'] == 'toml':
                    import tomllib
                    text_data=data.decode('utf-8')
                    parsed=tomllib.loads(text_data)
                    for key in dependency_module().IDENTITY_FIELDS:
                        if parsed.get(key) is not None and str(parsed[key]) in identity_map:
                            replacement=json.dumps(identity_map[str(parsed[key])],ensure_ascii=False)
                            text_data=re.sub(r'(?m)^'+re.escape(key)+r'\s*=\s*[^\n]+$',lambda _:key+' = '+replacement,text_data)
                    tomllib.loads(text_data)
                    data=text_data.encode('utf-8')
            plan_file(target,data,e['area'])
        if set(offsets) != ids:
            raise ValueError('Missing rollout payloads')
        for item in supplemental.get('files',[]):
            target = Path(item['target']).resolve()
            if target != (h/'.codex-global-state.json').resolve():
                raise ValueError('Invalid supplemental file target')
            plan_file(target,item['data'].encode('utf-8'),'global_state')
            file_plans[-1]['conflict']=False
        conflicts = [str(e['target']) for e in file_plans if e['conflict']]
        conflicts.extend(supplemental.get('conflicts',[]))
        db_plans, imported_counts = [], {}
        project_ids, section_ids = {}, {}
        rank = {'projects':0,'project_roots':1,'thread_sections':2,'threads':3,
                'thread_goals':4,'thread_goal_continuation_deferrals':5}
        for name, data in sorted(records.items(),key=lambda x:(not x[0].startswith('state_'),x[0])):
            target = contained(h,name)
            if not target.is_file():
                raise ValueError('Destination database missing: '+name+'. Initialize compatible Codex on destination first.')
            before = db_fingerprint(target)
            staged = tmp/('db-'+str(len(db_plans)))
            with ro_db(target) as c, rw_db(staged) as dest:
                c.backup(dest)
            prepared = map_value(data,mappings) if not name.startswith('sqlite/') else data
            c = sqlite3.connect(staged)
            c.row_factory = sqlite3.Row
            c.execute('PRAGMA foreign_keys=ON')
            try:
                for table, rows in prepared.items():
                    if table not in tables(c):
                        raise ValueError('Destination lacks table '+table+'; use a compatible Codex version')
                    if any(set(r)-columns(c,table).keys() for r in rows):
                        raise ValueError('Source columns missing on destination: '+table)
                # Match project identity by mapped roots; avoid foreign ID collisions.
                if 'projects' in prepared:
                    for row in prepared['projects']:
                        oldid = row['id']
                        roots = {normalized(r['path']) for r in prepared.get('project_roots',[]) if r['project_id']==oldid}
                        local = list(c.execute('SELECT * FROM project_roots')) if 'project_roots' in tables(c) else []
                        matches = {r['project_id'] for r in local if normalized(r['path']) in roots}
                        if len(matches)>1:
                            raise ValueError('Ambiguous destination project mapping')
                        existing = c.execute('SELECT * FROM projects WHERE id=?',(oldid,)).fetchone()
                        new_id = next(iter(matches)) if matches else (str(uuid.uuid5(uuid.NAMESPACE_URL,oldid+'|'+str(root))) if existing else oldid)
                        project_ids[oldid] = new_id
                        row['id'] = new_id
                        if matches:
                            # Reuse destination project metadata, preserve user's name/order.
                            row.update(dict(c.execute('SELECT * FROM projects WHERE id=?',(new_id,)).fetchone()))
                if 'thread_sections' in prepared:
                    for row in prepared['thread_sections']:
                        oldid=row['id']
                        match=c.execute('SELECT * FROM thread_sections WHERE name=?',(row['name'],)).fetchone()
                        existing=c.execute('SELECT * FROM thread_sections WHERE id=?',(oldid,)).fetchone()
                        row['id']=match['id'] if match else (str(uuid.uuid5(uuid.NAMESPACE_URL,oldid+'|'+str(h))) if existing else oldid)
                        section_ids[oldid]=row['id']
                        if match: row.update(dict(match))
                with c:
                    for table in sorted(prepared,key=lambda t:(rank.get(t,10),t)):
                        for row in prepared[table]:
                            if row.get('project_id') in project_ids:
                                row['project_id']=project_ids[row['project_id']]
                            if row.get('thread_section_id') in section_ids:
                                row['thread_section_id']=section_ids[row['thread_section_id']]
                            if table=='threads':
                                row['rollout_path']=str(contained(h,m['rollouts'][row['id']]))
                                if row.get('history_mode')=='paginated' and not any(any(r.get('thread_id')==row['id'] for r in d.get('thread_history_projection_state',[])) for n,d in records.items() if n.startswith('thread_history_')):
                                    raise ValueError('Missing required paginated history')
                            if table=='queued_thread_revisions':
                                existing=c.execute('SELECT revision FROM queued_thread_revisions WHERE thread_id=?',(row['thread_id'],)).fetchone()
                                row['revision']=existing[0] if existing else c.execute('SELECT COALESCE(MAX(revision),0)+1 FROM queued_thread_revisions').fetchone()[0]
                            for field in ('rollout_byte_offset','rollout_end_byte_offset','next_rollout_byte_offset'):
                                if row.get(field) is not None:
                                    try: row[field]=offsets[row['thread_id']][row[field]]
                                    except KeyError: raise ValueError('History offset is not a rollout line boundary')
                        upsert_rows(c,table,prepared[table],conflicts)
                        imported_counts[name+'/'+table]=len(prepared[table])
                    if c.execute('PRAGMA foreign_key_check').fetchone():
                        raise ValueError('Foreign key check failed')
                if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                    raise ValueError('Database integrity check failed')
            finally:
                c.close()
            db_plans.append({'target':target,'staged':staged,'before':before,'records':prepared,'rank':rank})
        # Reconcile desktop project references with the IDs selected by the DB merge.
        resolved_ids = {**identity_map, **project_ids, **section_ids}
        if resolved_ids != identity_map:
            revised = dependency_module().prepare(m.get('supplemental',{}), h, mappings, map_value, resolved_ids)
            conflicts = [c for c in conflicts if c not in supplemental.get('conflicts',[])]
            conflicts.extend(revised.get('conflicts',[]))
            for item in revised.get('files',[]):
                plan = next(p for p in file_plans if str(p['target']) == item['target'])
                raw = item['data'].encode('utf-8')
                plan['staged'].write_bytes(raw)
                plan['sha256'] = sha(raw)
            for plan in file_plans:
                if plan['target'].suffix.lower() == '.toml' and plan['area']=='codex':
                    import tomllib
                    text_data = plan['staged'].read_text(encoding='utf-8')
                    for key in ('project_id','thread_section_id'):
                        value = tomllib.loads(text_data).get(key)
                        if value in resolved_ids:
                            text_data=re.sub(r'(?m)^'+key+r'\s*=\s*[^\n]+$',lambda _:key+' = '+json.dumps(resolved_ids[value]),text_data)
                    raw=text_data.encode('utf-8'); plan['staged'].write_bytes(raw); plan['sha256']=sha(raw)
                    plan['conflict']=plan['before'] is not None and plan['before']!=plan['sha256']
        for name, rows in indices.items():
            if name not in {'session_index.jsonl','history.jsonl'}:
                raise ValueError('Invalid index destination')
            if any(r.get('id',r.get('session_id')) not in ids for r in rows):
                raise ValueError('Unrelated index row')
            target=contained(h,name)
            existing=[json.loads(line) for line in target.read_text(encoding='utf-8').splitlines() if line] if target.exists() else []
            mine=[r for r in existing if r.get('id',r.get('session_id')) in ids]
            incoming=map_value(rows,mappings)
            if mine and sorted(map(dumps,mine)) != sorted(map(dumps,incoming)):
                conflicts.append('Existing selected index entries differ: '+name)
            kept=[r for r in existing if r.get('id',r.get('session_id')) not in ids]
            plan_file(target,b''.join(dumps(r)+b'\n' for r in kept+incoming),'index')
            file_plans[-1]['conflict']=False  # Selected-entry conflicts were checked above.
        result={'session_id':sid,'session_count':len(ids),'file_count':len(file_plans),
                'database_rows':imported_counts,'path_mappings':mappings,'conflicts':sorted(set(conflicts)),
                'excluded_count':len(m.get('excluded',[])),'unresolved_references':m.get('unresolved_references',[]),
                'blockers':blockers,'status':'preview','restoration_scope':'persisted local state',
                'ui_visibility':'Not verified; verify through Codex after import',
                'scheduler_verification':'Not verified' if m.get('supplemental',{}).get('automation_ids') else 'not applicable'}
        if not args.apply:
            return result
        if conflicts and args.conflict!='replace':
            raise ValueError('Conflicts detected. Review preview; use --conflict replace only for authorized replacement.')
        destination_offline(h)
        backup=h/'session-transfer'/'backups'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
        backup.mkdir(parents=True)
        journal=[]
        connections=[]
        committed=[]
        try:
            # Lock every affected DB before freshness verification and hold until commits.
            for plan in db_plans:
                c=sqlite3.connect(plan['target'],timeout=5)
                c.row_factory=sqlite3.Row
                c.execute('PRAGMA foreign_keys=ON')
                c.execute('BEGIN IMMEDIATE')
                connections.append((c,plan))
                if db_fingerprint(plan['target'])!=plan['before']:
                    raise ValueError('Destination database changed during preparation; retry import')
            for entry in file_plans:
                target=entry['target']
                current=file_sha(target) if target.exists() else None
                if current!=entry['before']:
                    raise ValueError('Destination file changed during preparation: '+str(target))
            # Persist rollback material before mutating any live state.
            for index,(c,plan) in enumerate(connections):
                saved=backup/('db-'+str(index))
                with ro_db(plan['target']) as src,rw_db(saved) as dst: src.backup(dst)
                journal.append({'target':str(plan['target']),'saved':str(saved),'existed':True,'kind':'database'})
            for index,entry in enumerate(file_plans):
                if entry['before']==entry['sha256']: continue
                target=entry['target']; saved=backup/('file-'+str(index))
                if target.exists(): shutil.copy2(target,saved)
                journal.append({'target':str(target),'saved':str(saved),'existed':target.exists(),'kind':entry['area']})
            journal_write(backup/'journal.json',{'status':'applying','entries':journal})
            for c,plan in connections:
                for table in sorted(plan['records'],key=lambda t:(rank.get(t,10),t)):
                    upsert_rows(c,table,plan['records'][table],[])
                if c.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Live foreign key check failed')
            for entry in file_plans:
                if entry['before']==entry['sha256']: continue
                target=entry['target']
                target.parent.mkdir(parents=True,exist_ok=True)
                new=target.with_name(target.name+'.transfer-'+uuid.uuid4().hex)
                shutil.copy2(entry['staged'],new)
                new.replace(target)
            root.mkdir(parents=True,exist_ok=True)
            journal_write(backup/'journal.json',{'status':'committing','entries':journal})
            for c,plan in connections:
                c.commit(); committed.append(str(plan['target']))
            result.update(status='imported' if not blockers else 'imported_incomplete',backup=str(backup))
            journal_write(backup/'journal.json',{'status':'complete','entries':journal})
            journal_write(backup/'result.json',result)
        except BaseException:
            for c,plan in connections:
                try: c.rollback()
                except sqlite3.Error: pass
            for c,plan in connections: c.close()
            connections=[]
            if committed:
                journal_write(backup/'journal.json',{'status':'recovery_required','entries':journal,'committed_databases':committed})
            else:
                restore_entries([e for e in journal if e['kind']!='database'])
                journal_write(backup/'journal.json',{'status':'rolled_back','entries':journal})
            raise
        finally:
            for c,plan in connections: c.close()
        return result


def restore_entries(entries):
    for e in reversed(entries):
        p, saved = Path(e['target']), Path(e['saved'])
        if e['existed']:
            if e['kind'] == 'database':
                with ro_db(saved) as source, rw_db(p) as dest:
                    source.backup(dest)
            else:
                shutil.copy2(saved, p)
        elif p.exists():
            p.unlink()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='operation', required=True)
    e = sub.add_parser('export')
    e.add_argument('--session-id', required=True)
    e.add_argument('--folder')
    e.add_argument('--project-root')
    e.add_argument('--project-mode', choices=['none'], default='none', help='Session-only exports never copy the project directory')
    e.add_argument('--single', action='store_true', help='Exclude spawned descendants')
    e.add_argument('--live-snapshot', action='store_true', help='Freeze persisted history prefixes while the source task is active; later updates are outside the backup')
    e.add_argument('--include', action='append', help='Explicit session attachment FILE; no directories or instruction files')
    i = sub.add_parser('import')
    i.add_argument('--zip', required=True)
    i.add_argument('--session-id')
    i.add_argument('--project-root', required=True)
    i.add_argument('--identity-map', action='append', help='Explicit source=destination identity binding')
    i.add_argument('--allow-incomplete', action='store_true', help='Diagnostic restore; never reports complete')
    i.add_argument('--map', action='append', help='Additional OLD=NEW path mapping')
    i.add_argument('--apply', action='store_true')
    i.add_argument('--offline-confirmed', action='store_true')
    i.add_argument('--conflict', choices=['abort', 'replace'], default='abort')
    v = sub.add_parser('inspect')
    v.add_argument('--zip', required=True)
    for command in (e, i, v):
        command.add_argument('--codex-home')
        command.add_argument('--max-bytes', type=int, default=2*1024**3)
    args = p.parse_args()
    try:
        if args.operation == 'export':
            result = export_session(args)
        elif args.operation == 'import':
            result = import_session(args)
        else:
            z, m, r, _ = read_bundle(Path(args.zip), args.max_bytes)
            z.close()
            result = {'manifest': m, 'database_row_counts': {n: {t: len(rows) for t, rows in d.items()} for n, d in r.items()}}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, sqlite3.Error, zipfile.BadZipFile, KeyError) as ex:
        print(json.dumps({'error': str(ex)}), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

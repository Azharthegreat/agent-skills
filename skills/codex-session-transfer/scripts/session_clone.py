"""Prepare a verified independent clone archive; use native APIs for history checks.

This module never directly changes an existing Codex database. Full archive import
still uses session_transfer's offline transaction and conflict checks.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import uuid
import zipfile
from urllib.parse import unquote

import session_transfer as transfer

RELATIONAL_FIELDS = {'id', 'turn_id', 'item_id', 'artifact_id', 'goal_id',
                     'automation_id', 'run_id', 'project_id', 'thread_section_id',
                     'section_id', 'client_id', 'queued_item_id', 'queue_item_id'}
OPAQUE_FIELDS = {'encrypted_content', 'signature', 'capability_token', 'token'}
PROSE_FIELDS = {'text', 'message', 'prompt', 'raw_memory', 'summary', 'title', 'name'}
OFFSET_FIELDS = {'rollout_byte_offset', 'rollout_end_byte_offset', 'next_rollout_byte_offset'}


def identity_maps(manifest, records, new_session_id=None):
    ids = set(manifest['session_ids'])
    for tables in records.values():
        for rows in tables.values():
            for row in rows:
                for key in RELATIONAL_FIELDS & row.keys():
                    value = row[key]
                    if value is None:
                        continue
                    if not isinstance(value, str) or value.isdecimal():
                        raise ValueError('Cannot safely clone numeric relational identity: '+key)
                    if value:
                        ids.add(value)
    ids.update(manifest.get('supplemental', {}).get('automation_ids', []))
    result = {old: str(uuid.uuid4()) for old in sorted(ids)}
    if new_session_id:
        candidate = str(uuid.UUID(new_session_id))
        if candidate in ids:
            raise ValueError('Clone session ID must differ from all source identities')
        result[manifest['session_id']] = candidate
    return result


def remapper(mapping):
    # Boundaries preserve longer, unrelated identifiers and opaque encrypted data.
    pattern = re.compile('|'.join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
    uuid_keys = {value for value in mapping if re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', value)}

    def rewrite(value, key=None):
        if key in OPAQUE_FIELDS:
            return value
        if isinstance(value, str):
            if value in mapping and (key not in PROSE_FIELDS or value in uuid_keys):
                return mapping[value]
            # Embedded JSON needs recursion so opaque fields remain untouched.
            if value.lstrip().startswith(('{', '[')):
                try:
                    parsed = json.loads(value)
                    return json.dumps(rewrite(parsed), ensure_ascii=False, separators=(',', ':'))
                except (ValueError, TypeError):
                    pass
            def substitute(match):
                old = match.group()
                # UI keys preserve URL-encoded separators such as local%3AUUID.
                # Judge token boundaries after decoding adjacent characters,
                # without reserializing or changing the key's encoded syntax.
                left = unquote(value[max(0, match.start()-3):match.start()])[-1:]
                right = unquote(value[match.end():match.end()+3])[:1]
                if (left and (left.isalnum() or left == '_')) or (right and (right.isalnum() or right == '_')):
                    return old
                # Non-UUID relational IDs can be ordinary words. Rewrite their
                # path/quoted references, while preserving freeform narrative.
                before = value[match.start()-1:match.start()] if match.start() else ''
                after = value[match.end():match.end()+1]
                if old in uuid_keys or (before in {'/', '\\', '"', "'"} and after in {'/', '\\', '"', "'", '.'}):
                    return mapping[old]
                return old
            return pattern.sub(substitute, value)
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                newkey = rewrite(k)
                if newkey in result:
                    raise ValueError('Identity rewrite produced duplicate object keys')
                result[newkey] = rewrite(v, k)
            return result
        return value
    return rewrite


def rollout_order(archive, manifest):
    """Parent rollouts precede thin forks so inherited byte offsets can be rebuilt."""
    entries = {entry['path']: entry for entry in manifest['files'] if entry['kind'] == 'rollout'}
    ordered, visiting, done = [], set(), set()
    def visit(sid):
        if sid in done:
            return
        if sid in visiting:
            raise ValueError('Cyclic rollout history_base dependency')
        visiting.add(sid)
        entry = entries[manifest['rollouts'][sid]]
        with archive.open(entry['archive']) as stream:
            first = json.loads(stream.readline())
        base = first.get('payload', {}).get('history_base')
        if base:
            parent = base['thread_id']
            if parent not in manifest['rollouts']:
                raise ValueError('Clone requires missing history_base parent: '+parent)
            visit(parent)
        visiting.remove(sid)
        done.add(sid)
        ordered.append(entry)
    for sid in manifest['session_ids']:
        visit(sid)
    return ordered + [entry for entry in manifest['files'] if entry['kind'] != 'rollout']


def clone_bundle(source, folder, *, new_session_id=None, max_bytes=20_000_000_000):
    source = Path(source).resolve()
    z, manifest, records, indices = transfer.read_bundle(source, max_bytes)
    with z:
        mapping = identity_maps(manifest, records, new_session_id)
        rewrite = remapper(mapping)
        cloned = rewrite(copy.deepcopy(manifest))
        cloned_records = rewrite(records)
        cloned_indices = rewrite(indices)
        offsets = {}
        payloads = []
        newentries = {old['archive']: new for old, new in zip(manifest['files'], cloned['files'])}
        for entry in rollout_order(z, manifest):
            newentry = newentries[entry['archive']]
            data = z.read(entry['archive'])
            if entry['kind'] == 'rollout':
                sid = next(i for i, path in manifest['rollouts'].items() if path == entry['path'])
                oldpos = newpos = 0
                positions = {0: 0}
                chunks = []
                for line in data.splitlines(keepends=True):
                    row = json.loads(line)
                    if row.get('type') == 'session_meta':
                        base = row.get('payload', {}).get('history_base')
                        if base and base.get('end_byte_offset') is not None:
                            try:
                                base['end_byte_offset'] = offsets[mapping[base['thread_id']]][base['end_byte_offset']]
                            except KeyError:
                                raise ValueError('Invalid inherited history byte offset') from None
                    chunk = transfer.dumps(rewrite(row)) + b'\n'
                    chunks.append(chunk)
                    oldpos += len(line)
                    newpos += len(chunk)
                    positions[oldpos] = newpos
                data = b''.join(chunks)
                offsets[mapping[sid]] = positions
            elif entry['kind'] in {'text', 'toml'}:
                data = rewrite(data.decode('utf-8')).encode('utf-8')
                if entry['kind'] == 'toml':
                    import tomllib
                    tomllib.loads(data.decode('utf-8'))
            newentry['size'], newentry['sha256'] = len(data), transfer.sha(data)
            payloads.append((newentry['archive'], data))
        for tables in cloned_records.values():
            for rows in tables.values():
                for row in rows:
                    for field in OFFSET_FIELDS & row.keys():
                        if row[field] is not None:
                            try:
                                row[field] = offsets[row['thread_id']][row[field]]
                            except KeyError:
                                raise ValueError('Cannot map clone history offset to rollout boundary') from None
        if cloned.get('supplemental') is not None:
            cloned['supplemental']['records'] = {name: data for name, data in cloned_records.items() if name.startswith('sqlite/')}
        cloned['clone'] = {'source_session_id': manifest['session_id'],
                           'source_archive_sha256': transfer.file_sha(source),
                           'identity_map': mapping, 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        outdir = Path(folder).resolve()
        outdir.mkdir(parents=True, exist_ok=True)
        output = outdir / (cloned['session_id']+'.zip')
        partial = output.with_suffix('.zip.partial')
        if output.exists() or partial.exists():
            raise ValueError('Clone output already exists')
        try:
            with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as target:
                for name, data in payloads:
                    target.writestr(name, data)
                for name, content in [('records', cloned_records), ('indices', cloned_indices)]:
                    data = transfer.dumps(content)
                    cloned[name+'_sha256'] = transfer.sha(data)
                    target.writestr(name+'.json', data)
                target.writestr('manifest.json', transfer.dumps(cloned))
            checked, _, _, _ = transfer.read_bundle(partial, max_bytes)
            checked.close()
            # Exclusive output creation prevents concurrent overwrite.
            with output.open('xb') as dst, partial.open('rb') as src:
                import shutil
                shutil.copyfileobj(src, dst)
            return {'zip': str(output), 'session_id': cloned['session_id'],
                    'session_ids': cloned['session_ids'], 'identity_map': mapping,
                    'sha256': transfer.file_sha(output), 'status': 'clone_archive_verified'}
        finally:
            if partial.exists():
                partial.unlink()


class AppServer:
    """Bounded stdio JSON-RPC client. Caller supplies the trusted installed binary."""
    METHODS = {'thread/read', 'thread/list', 'thread/turns/list', 'thread/items/list',
               'thread/fork', 'thread/resume', 'thread/name/set', 'initialize'}

    def __init__(self, binary, codex_home, timeout=40):
        self.binary = Path(binary).resolve(strict=True)
        if self.binary.name.lower() not in {'codex', 'codex.exe'}:
            raise ValueError('Specify the trusted installed Codex binary')
        self.home = transfer.fs_path(codex_home)
        if not self.home.is_dir():
            raise ValueError('Codex home does not exist')
        self.timeout = timeout
        self.messages = queue.Queue(maxsize=10000)
        self.counter = 0
        self.process = None

    def __enter__(self):
        env = dict(os.environ)
        env['CODEX_HOME'] = str(self.home)
        self.process = subprocess.Popen([str(self.binary), 'app-server', '--stdio'],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, encoding='utf-8', env=env)
        def receive():
            try:
                for line in self.process.stdout:
                    try:
                        self.messages.put(json.loads(line), timeout=1)
                    except (ValueError, queue.Full):
                        self.messages.put_nowait({'_error': 'Invalid or excessive app-server output'})
                        break
            finally:
                try:
                    self.messages.put_nowait({'_error': 'App-server disconnected'})
                except queue.Full:
                    pass
        threading.Thread(target=receive, daemon=True).start()
        try:
            info = self.request('initialize', {'clientInfo': {'name': 'session_transfer', 'version': '2'},
                                              'capabilities': {'experimentalApi': True}})
            if transfer.fs_path(info['codexHome']) != self.home:
                raise ValueError('App-server initialized an unexpected Codex home')
            self._send({'method': 'initialized'})
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def _send(self, payload):
        self.process.stdin.write(json.dumps(payload)+'\n')
        self.process.stdin.flush()

    def request(self, method, params):
        if method not in self.METHODS:
            raise ValueError('App-server method outside transfer scope')
        self.counter += 1
        self._send({'id': self.counter, 'method': method, 'params': params})
        deadline = time.monotonic()+self.timeout
        while time.monotonic() < deadline:
            try:
                message = self.messages.get(timeout=max(.01, deadline-time.monotonic()))
            except queue.Empty:
                raise TimeoutError('App-server request timed out: '+method) from None
            if '_error' in message:
                raise RuntimeError(message['_error'])
            if message.get('id') == self.counter:
                if 'error' in message:
                    raise RuntimeError('App-server '+method+': '+message['error'].get('message', 'error'))
                return message['result']
            # Never approve or execute server-initiated tool requests.
            if 'method' in message and 'id' in message:
                self._send({'id': message['id'], 'error': {'code': -32601, 'message': 'Transfer verification does not execute tools'}})
        raise TimeoutError('App-server request timed out: '+method)

    def pages(self, method, params, max_pages=10000):
        result, seen = [], set()
        for _ in range(max_pages):
            page = self.request(method, params)
            result.extend(page['data'])
            cursor = page.get('nextCursor')
            if cursor is None:
                return result
            if cursor in seen:
                raise ValueError('App-server pagination cursor repeated')
            seen.add(cursor)
            params = dict(params, cursor=cursor)
        raise ValueError('App-server pagination limit exceeded')

    def verify(self, session_id):
        thread = self.request('thread/read', {'threadId': session_id, 'includeTurns': False})['thread']
        if thread['id'] != session_id:
            raise ValueError('App-server returned an unexpected session')
        turns = self.pages('thread/turns/list', {'threadId': session_id, 'itemsView': 'full', 'sortDirection': 'asc', 'limit': 100})
        items = self.pages('thread/items/list', {'threadId': session_id, 'sortDirection': 'asc', 'limit': 100})
        # Native registration/projection can finish shortly after a fork response.
        # The normal list API repairs metadata from persisted rollout history.
        listed = False
        for attempt in range(6):
            threads = self.pages('thread/list', {'limit': 100})
            listed = any(t['id'] == session_id for t in threads)
            if listed:
                break
            time.sleep(.2)
        if not listed:
            raise ValueError('Restored thread missing from native thread list')
        return {'session_id': session_id, 'turn_count': len(turns), 'item_count': len(items),
                'history_sha256': hashlib.sha256(transfer.dumps(turns)).hexdigest(),
                'listed': listed, 'path': thread.get('path'), 'history_mode': thread.get('historyMode'),
                'ui_visibility': 'Not verified; native list membership verified'}

    def fork(self, source_id, rollout, cwd, **overrides):
        result = self.request('thread/fork', dict(threadId=source_id, path=str(Path(rollout).resolve(strict=True)),
                              cwd=str(Path(cwd).resolve(strict=True)), deferGoalContinuation=True,
                              excludeTurns=True, **overrides))
        if result['thread']['id'] == source_id:
            raise ValueError('Native fork did not create a new identity')
        return result['thread']

    def __exit__(self, *_):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    clone = commands.add_parser('prepare')
    clone.add_argument('--zip', required=True)
    clone.add_argument('--folder', required=True)
    clone.add_argument('--new-session-id')
    clone.add_argument('--max-bytes', type=int, default=20_000_000_000)
    verify = commands.add_parser('verify-native')
    verify.add_argument('--codex-binary', required=True)
    verify.add_argument('--codex-home', required=True)
    verify.add_argument('--session-id', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = clone_bundle(args.zip, args.folder, new_session_id=args.new_session_id, max_bytes=args.max_bytes)
    else:
        with AppServer(args.codex_binary, args.codex_home) as client:
            result = client.verify(args.session_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

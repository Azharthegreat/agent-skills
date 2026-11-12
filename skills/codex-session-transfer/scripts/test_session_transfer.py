import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('transfer', Path(__file__).with_name('session_transfer.py'))
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
SID = '11111111-1111-4111-8111-111111111111'
CHILD = '22222222-2222-4222-8222-222222222222'
OTHER = '33333333-3333-4333-8333-333333333333'


def init(home):
    home.mkdir(parents=True)
    with t.rw_db(home/'state_5.sqlite') as c:
        c.executescript('CREATE TABLE threads(id TEXT PRIMARY KEY,rollout_path TEXT,cwd TEXT,title TEXT,history_mode TEXT);'
                        'CREATE TABLE thread_spawn_edges(parent_thread_id TEXT,child_thread_id TEXT PRIMARY KEY,status TEXT);'
                        'CREATE TABLE thread_artifacts(id TEXT PRIMARY KEY,thread_id TEXT,payload TEXT);')
    with t.rw_db(home/'thread_history_1.sqlite') as c:
        c.executescript('CREATE TABLE thread_turns(thread_id TEXT,turn_id TEXT,rollout_byte_offset INTEGER,rollout_end_byte_offset INTEGER,PRIMARY KEY(thread_id,turn_id));'
                        'CREATE TABLE thread_items(thread_id TEXT,item_id TEXT,item_json TEXT,PRIMARY KEY(thread_id,item_id));'
                        'CREATE TABLE thread_history_projection_state(thread_id TEXT PRIMARY KEY,next_rollout_byte_offset INTEGER,next_rollout_ordinal INTEGER);')


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source, self.dest = self.base/'old-user'/'.codex', self.base/'different-user'/'.codex'
        self.project, self.newproject = self.base/'server-code', self.base/'laptop-project-long-name'
        init(self.source)
        init(self.dest)
        self.project.mkdir()
        (self.project/'main.py').write_text('print("kept")\n')
        (self.project/'.env').write_text('SECRET=value')
        (self.source/'auth.json').write_text('DO NOT EXPORT')
        asset = self.source/'attachments'/'unrelated-asset-id'/'picture.png'
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b'\x89PNG\x00fixture')
        self.asset = asset
        for sid in (SID, CHILD):
            rollout = self.source/'sessions'/'2026'/'09'/'09'/('rollout-'+sid+'.jsonl')
            rollout.parent.mkdir(parents=True, exist_ok=True)
            lines = [t.dumps({'type':'session_meta','payload':{'id':sid,'cwd':str(self.project)}})+b'\n',
                     t.dumps({'type':'response_item','payload':{'text':'See '+str(asset)+' and '+str(self.project/'main.py'),'encrypted_content':'unchanged'}})+b'\n']
            rollout.write_bytes(b''.join(lines))
            with t.rw_db(self.source/'state_5.sqlite') as c:
                c.execute('INSERT INTO threads VALUES(?,?,?,?,?)',(sid,str(rollout),str(self.project),'Fixture title','paginated'))
            with t.rw_db(self.source/'thread_history_1.sqlite') as c:
                c.execute('INSERT INTO thread_turns VALUES(?,?,?,?)',(sid,'turn1',len(lines[0]),sum(map(len,lines))))
                c.execute('INSERT INTO thread_items VALUES(?,?,?)',(sid,'item1',json.dumps({'path':str(asset)})))
                c.execute('INSERT INTO thread_history_projection_state VALUES(?,?,?)',(sid,sum(map(len,lines)),2))
        with t.rw_db(self.source/'state_5.sqlite') as c:
            c.execute('INSERT INTO thread_spawn_edges VALUES(?,?,?)',(SID,CHILD,'completed'))
        with t.rw_db(self.dest/'state_5.sqlite') as c:
            c.execute('INSERT INTO threads VALUES(?,?,?,?,?)',(OTHER,'unrelated','unrelated','Keep me','legacy'))
        (self.source/'session_index.jsonl').write_bytes(t.dumps({'id':SID,'thread_name':'Fixture','updated_at':'2026-09-09'})+b'\n')
        self.args = argparse.Namespace(session_id=SID,codex_home=str(self.source),project_root=str(self.project),project_mode='none',single=False,include=[str(self.project/'main.py')],folder=str(self.base/'exports'),max_bytes=10000000)

    def export(self):
        return Path(t.export_session(self.args)['zip'])

    def imp(self, zip_path, **changes):
        args = argparse.Namespace(zip=str(zip_path),codex_home=str(self.dest),project_root=str(self.newproject),map=[],apply=False,offline_confirmed=False,session_id=SID,conflict='abort',max_bytes=10000000)
        for k,v in changes.items():
            setattr(args,k,v)
        with patch.object(t,'no_codex_processes'):
            return t.import_session(args)

    def test_roundtrip_paths_assets_offsets_unrelated_and_idempotence(self):
        z = self.export()
        before = t.file_sha(self.dest/'state_5.sqlite')
        self.assertEqual(self.imp(z)['status'],'preview')
        self.assertEqual(before,t.file_sha(self.dest/'state_5.sqlite'))
        self.assertFalse(self.newproject.exists())
        result = self.imp(z,apply=True,offline_confirmed=True)
        self.assertEqual(result['session_count'],2)
        self.assertEqual((self.newproject/'main.py').read_text(),'print("kept")\n')
        self.assertFalse((self.newproject/'.env').exists())
        self.assertFalse((self.dest/'auth.json').exists())
        restored_asset = self.dest/self.asset.relative_to(self.source)
        self.assertEqual(restored_asset.read_bytes(),self.asset.read_bytes())
        with t.rw_db(self.dest/'state_5.sqlite') as c:
            self.assertEqual(c.execute('select title from threads where id=?',(OTHER,)).fetchone()[0],'Keep me')
            path,cwd = c.execute('select rollout_path,cwd from threads where id=?',(SID,)).fetchone()
        self.assertEqual(cwd,str(self.newproject.resolve()))
        lines = Path(path).read_bytes().splitlines(keepends=True)
        self.assertIn(str(restored_asset.resolve()),json.loads(lines[1])['payload']['text'])
        self.assertEqual(json.loads(lines[1])['payload']['encrypted_content'],'unchanged')
        with t.rw_db(self.dest/'thread_history_1.sqlite') as c:
            self.assertEqual(c.execute('select rollout_byte_offset,rollout_end_byte_offset from thread_turns where thread_id=?',(SID,)).fetchone(),(len(lines[0]),sum(map(len,lines))))
            self.assertEqual(c.execute('select next_rollout_byte_offset from thread_history_projection_state where thread_id=?',(SID,)).fetchone()[0],sum(map(len,lines)))
        self.assertEqual(self.imp(z)['conflicts'],[])

    def test_conflict_aborts_and_explicit_replace_backs_up(self):
        z = self.export()
        self.newproject.mkdir()
        (self.newproject/'main.py').write_text('local change')
        with self.assertRaisesRegex(ValueError,'Conflicts'):
            self.imp(z,apply=True,offline_confirmed=True)
        self.assertEqual((self.newproject/'main.py').read_text(),'local change')
        result = self.imp(z,apply=True,offline_confirmed=True,conflict='replace')
        self.assertTrue((Path(result['backup'])/'journal.json').exists())

    def test_zip_traversal_rejected(self):
        z = self.export()
        with zipfile.ZipFile(z,'a') as f:
            f.writestr('../escape.txt','bad')
        with self.assertRaisesRegex(ValueError,'Unsafe archive'):
            self.imp(z)

    def test_wrong_session_rejected(self):
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.imp(self.export(),session_id=OTHER)

    def test_corrupt_content_rejected(self):
        z = self.export()
        with zipfile.ZipFile(z) as source:
            data = {n:source.read(n) for n in source.namelist()}
        name = next(n for n in data if n.endswith('main.py'))
        data[name] = b'bad'
        with zipfile.ZipFile(z,'w') as target:
            for n,v in data.items():
                target.writestr(n,v)
        with self.assertRaisesRegex(ValueError,'size mismatch|checksum mismatch'):
            self.imp(z)

    def test_offline_required(self):
        with self.assertRaisesRegex(ValueError,'offline-confirmed'):
            self.imp(self.export(),apply=True)

    def test_schema_mismatch_rejected(self):
        z = self.export()
        with t.rw_db(self.dest/'thread_history_1.sqlite') as c:
            c.execute('DROP TABLE thread_items')
        with self.assertRaisesRegex(ValueError,'lacks table'):
            self.imp(z)

    def test_boundary_mapping_and_agent_addresses(self):
        self.assertEqual(t.map_value('C:\\code\\a C:\\code-other\\a /root/worker',[('C:\\code','D:\\projects\\my-app')]),'D:\\projects\\my-app\\a C:\\code-other\\a /root/worker')

    def test_invalid_offset_rejected(self):
        with t.rw_db(self.source/'thread_history_1.sqlite') as c:
            c.execute('update thread_turns set rollout_byte_offset=1')
        with self.assertRaisesRegex(ValueError,'line boundary'):
            self.imp(self.export())

    def test_goal_status_is_restored(self):
        with t.rw_db(self.source/'goals_1.sqlite') as c:
            c.execute('CREATE TABLE thread_goals(thread_id TEXT PRIMARY KEY,objective TEXT,status TEXT)')
            c.execute('INSERT INTO thread_goals VALUES(?,?,?)',(SID,'Do some work','active'))
        with t.rw_db(self.dest/'goals_1.sqlite') as c:
            c.execute('CREATE TABLE thread_goals(thread_id TEXT PRIMARY KEY,objective TEXT,status TEXT)')
        z = self.export()
        with zipfile.ZipFile(z) as archive:
            self.assertIn('goals_1.sqlite',json.loads(archive.read('records.json')))
        self.imp(z,apply=True,offline_confirmed=True)
        with t.rw_db(self.dest/'goals_1.sqlite') as c:
            self.assertEqual(c.execute('SELECT status FROM thread_goals WHERE thread_id=?',(SID,)).fetchone()[0],'active')

    def test_size_limit_and_archive_name(self):
        self.args.max_bytes = 1
        with self.assertRaisesRegex(ValueError,'exceeds'):
            self.export()
        self.args.max_bytes = 10000000
        self.assertEqual(self.export().name,SID+'.zip')

    def test_process_guard_rejects_live_codex(self):
        import os
        from types import SimpleNamespace
        output = '"Codex.exe","123","Console","1","100 K"\n' if os.name == 'nt' else 'codex\n'
        with patch.object(t.subprocess,'run',return_value=SimpleNamespace(stdout=output)):
            with self.assertRaisesRegex(ValueError,'Close Codex'):
                t.no_codex_processes()


if __name__ == '__main__':
    unittest.main()

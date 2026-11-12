import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile
import test_session_transfer as f

t=f.t


class RobustnessTests(unittest.TestCase):
    def test_session_only_export_ignores_workspace_and_instructions(self):
        c=self.c;c.args.include=[]
        for name in ('CLAUDE.md','AGENTS.md','agent.md','unrelated.txt'):
            (c.project/name).write_text('must not be copied')
        memory=c.source/'memories';memory.mkdir()
        (memory/'shared.md').write_text('unowned memory')
        asset=c.source/'attachments'/f.SID;asset.mkdir(parents=True)
        (asset/'AGENTS.md').write_text('do not copy even under a session folder')
        skill=c.source/'skills/demo';skill.mkdir(parents=True)
        (skill/'SKILL.md').write_text('unrelated skill')
        with zipfile.ZipFile(c.export()) as archive:
            m=json.loads(archive.read('manifest.json'))
            self.assertEqual(m['project_mode'],'none')
            self.assertTrue(all(e['area']=='codex' for e in m['files']))
            self.assertFalse(any(Path(e['path']).name.casefold() in {'agents.md','agent.md','claude.md','skill.md','shared.md','main.py'} for e in m['files']))
            self.assertEqual(len([e for e in m['files'] if e['kind']=='rollout']),2)

    def setUp(self):
        self.c=f.TransferTests(); self.c.setUp()
        self.addCleanup(self.c.doCleanups)

    def test_metadata_and_index_conflict_no_cascade(self):
        c=self.c; z=c.export(); c.imp(z,apply=True,offline_confirmed=True)
        with t.rw_db(c.dest/'state_5.sqlite') as db:
            db.executescript('DROP TABLE thread_artifacts; CREATE TABLE thread_artifacts(id TEXT PRIMARY KEY,thread_id TEXT REFERENCES threads(id) ON DELETE CASCADE,payload TEXT);')
            db.execute('INSERT INTO thread_artifacts VALUES(?,?,?)',('keep',f.SID,'destination metadata'))
        self.assertEqual(c.imp(z)['conflicts'],[])
        c.imp(z,apply=True,offline_confirmed=True)
        with t.rw_db(c.dest/'state_5.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM thread_artifacts WHERE id="keep"').fetchone()[0],1)
        (c.dest/'session_index.jsonl').write_bytes(t.dumps({'id':f.SID,'thread_name':'changed'})+b'\n')
        self.assertTrue(c.imp(z)['conflicts'])
        with self.assertRaisesRegex(ValueError,'Conflicts'):
            c.imp(z,apply=True,offline_confirmed=True)

    def test_concurrent_destination_update_is_preserved(self):
        c=self.c; z=c.export(); calls=[]
        def gate():
            calls.append(1)
            if len(calls)==2:
                with t.rw_db(c.dest/'state_5.sqlite') as db:
                    db.execute('UPDATE threads SET title=? WHERE id=?',('Concurrent edit',f.OTHER))
        import argparse
        args=argparse.Namespace(zip=str(z),codex_home=str(c.dest),project_root=str(c.newproject),map=[],apply=True,offline_confirmed=True,session_id=f.SID,conflict='abort',max_bytes=10000000)
        with patch.object(t,'no_codex_processes',side_effect=gate):
            with self.assertRaisesRegex(ValueError,'changed during preparation'):
                t.import_session(args)
        with t.rw_db(c.dest/'state_5.sqlite') as db:
            self.assertEqual(db.execute('SELECT title FROM threads WHERE id=?',(f.OTHER,)).fetchone()[0],'Concurrent edit')
            self.assertEqual(db.execute('SELECT count(*) FROM threads WHERE id=?',(f.SID,)).fetchone()[0],0)

    def test_duplicate_include_keeps_real_destination(self):
        c=self.c; c.args.include=[str(c.project/'main.py')]
        z=c.export()
        with zipfile.ZipFile(z) as archive:
            self.assertEqual(json.loads(archive.read('manifest.json'))['extra_maps'],[])
        c.imp(z,apply=True,offline_confirmed=True)
        self.assertTrue((c.newproject/'main.py').exists())

    def test_imported_extra_survives_reexport(self):
        c=self.c; extra=c.base/'external.txt'; extra.write_text('keep extra')
        c.args.include=[str(extra)]; z=c.export(); c.imp(z,apply=True,offline_confirmed=True)
        c.args.codex_home=str(c.dest); c.args.project_root=str(c.newproject); c.args.folder=str(c.base/'second'); c.args.include=[]
        with zipfile.ZipFile(c.export()) as archive:
            self.assertTrue(any(e['path'].endswith('external.txt') for e in json.loads(archive.read('manifest.json'))['files']))

    def test_path_override_and_cross_platform(self):
        self.assertEqual(t.map_value('C:\\code\\src\\main.py',[('C:\\code','E:\\wanted'),('C:\\code','D:\\default')]),'E:\\wanted\\src\\main.py')
        self.assertEqual(t.map_value('C:\\code\\src\\main.py',[('C:\\code','/home/alice/project')]),'/home/alice/project/src/main.py')

    def test_extended_windows_root_matches_native_root(self):
        import os
        if os.name=='nt':
            self.assertEqual(t.fs_path('\\\\?\\C:\\code'),t.fs_path('C:\\code'))

    def test_live_snapshot_freezes_prefix_while_source_appends(self):
        c=self.c
        c.args.live_snapshot=True
        with t.ro_db(c.source/'state_5.sqlite') as db:
            rollout=Path(db.execute('SELECT rollout_path FROM threads WHERE id=?',(f.SID,)).fetchone()[0])
        before=rollout.read_bytes()
        original=zipfile.ZipFile.writestr
        def append_after_capture(archive,name,data,*args,**kwargs):
            result=original(archive,name,data,*args,**kwargs)
            if name=='records.json':
                with rollout.open('ab') as stream:
                    stream.write(t.dumps({'type':'event_msg','payload':{'type':'task_complete'}})+b'\n')
            return result
        with patch.object(zipfile.ZipFile,'writestr',new=append_after_capture):
            z=c.export()
        with zipfile.ZipFile(z) as archive:
            m=json.loads(archive.read('manifest.json'))
            entry=next(e for e in m['files'] if e['path']==m['rollouts'][f.SID])
            self.assertEqual(archive.read(entry['archive']),before)
            self.assertEqual(m['capture_mode'],'live persisted snapshot')

    def test_unrelated_binary_rollout_rejected(self):
        c=self.c; z=c.export()
        with zipfile.ZipFile(z) as source: entries={n:source.read(n) for n in source.namelist()}
        m=json.loads(entries['manifest.json']); raw=b'not a session'
        entry={'archive':'files/codex/sessions/unrelated.jsonl','area':'codex','path':'sessions/unrelated.jsonl','kind':'binary','size':len(raw),'sha256':t.sha(raw)}
        m['files'].append(entry); entries[entry['archive']]=raw; entries['manifest.json']=t.dumps(m)
        with zipfile.ZipFile(z,'w') as archive:
            for name,data in entries.items(): archive.writestr(name,data)
        with self.assertRaisesRegex(ValueError,'Unrelated or unvalidated'):
            c.imp(z)

    def test_metadata_counted_in_export_limit(self):
        c=self.c; z=c.export()
        with zipfile.ZipFile(z) as archive: size=sum(e['size'] for e in json.loads(archive.read('manifest.json'))['files'])
        c.args.max_bytes=size+1; c.args.folder=str(c.base/'limited')
        with self.assertRaisesRegex(ValueError,'metadata exceeds'):
            c.export()

    def test_missing_paginated_store_blocks_export(self):
        c=self.c; (c.source/'thread_history_1.sqlite').unlink()
        with self.assertRaisesRegex(ValueError,'Missing paginated'):
            c.export()

    def test_import_lock_blocks_second_import(self):
        c=self.c; z=c.export(); folder=c.dest/'session-transfer'; folder.mkdir(); (folder/'import.lock').write_text('other importer')
        with self.assertRaisesRegex(ValueError,'Another import'):
            c.imp(z,apply=True,offline_confirmed=True)

    def test_memory_schedule_and_queue_roundtrip(self):
        c=self.c
        memory=c.source/'memories'/(f.SID+'-notes.md'); memory.parent.mkdir(); memory.write_text('Shared memory preserved')
        adir=c.source/'automations'/'fixture'; adir.mkdir(parents=True)
        (adir/'automation.toml').write_text('id="fixture"\nname="fixture"\nprompt="fixture"\nstatus="ACTIVE"\nrrule="FREQ=DAILY"\nkind="cron"\ntarget_thread_id="'+f.SID+'"\n')
        schema='CREATE TABLE automations(id TEXT PRIMARY KEY,name TEXT,prompt TEXT,status TEXT,rrule TEXT,kind TEXT,target_thread_id TEXT);'
        for h in (c.source,c.dest):
            (h/'sqlite').mkdir()
            with t.rw_db(h/'sqlite/codex-dev.db') as db: db.executescript(schema)
            with t.rw_db(h/'queue_1.sqlite') as db:
                db.execute('CREATE TABLE queued_items(id TEXT PRIMARY KEY,thread_id TEXT,payload_json TEXT,queue_order INTEGER)')
        with t.rw_db(c.source/'sqlite/codex-dev.db') as db:
            db.execute('INSERT INTO automations VALUES(?,?,?,?,?,?,?)',('fixture','fixture','fixture','ACTIVE','FREQ=DAILY','cron',f.SID))
        with t.rw_db(c.source/'queue_1.sqlite') as db:
            db.execute('INSERT INTO queued_items VALUES(?,?,?,?)',('q1',f.SID,'{"text":"pending"}',1))
        c.imp(c.export(),apply=True,offline_confirmed=True)
        self.assertEqual((c.dest/'memories'/(f.SID+'-notes.md')).read_text(),'Shared memory preserved')
        self.assertTrue((c.dest/'automations/fixture/automation.toml').exists())
        with t.rw_db(c.dest/'sqlite/codex-dev.db') as db:
            self.assertEqual(db.execute('SELECT status FROM automations').fetchone()[0],'ACTIVE')
        with t.rw_db(c.dest/'queue_1.sqlite') as db:
            self.assertEqual(db.execute('SELECT queue_order FROM queued_items').fetchone()[0],1)

    def test_file_failure_rolls_back_uncommitted_databases(self):
        c=self.c; z=c.export(); original=t.shutil.copy2
        def fail(src,dst,*args,**kwargs):
            if '.transfer-' in str(dst): raise OSError('fixture disk failure')
            return original(src,dst,*args,**kwargs)
        with patch.object(t.shutil,'copy2',side_effect=fail):
            with self.assertRaisesRegex(OSError,'fixture disk failure'):
                c.imp(z,apply=True,offline_confirmed=True)
        with t.rw_db(c.dest/'state_5.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM threads WHERE id=?',(f.SID,)).fetchone()[0],0)
        self.assertFalse((c.dest/'session-transfer/import.lock').exists())


if __name__=='__main__': unittest.main()

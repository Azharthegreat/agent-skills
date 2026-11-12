import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import session_dependencies as dep

SID = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)/'source'
        self.home.mkdir()

    def db(self):
        (self.home/'sqlite').mkdir(exist_ok=True)
        c = sqlite3.connect(self.home/'sqlite/codex-dev.db')
        c.executescript('''
          CREATE TABLE automations(id TEXT PRIMARY KEY,target_thread_id TEXT,prompt TEXT,status TEXT,account_id TEXT);
          CREATE TABLE automation_runs(thread_id TEXT PRIMARY KEY,automation_id TEXT,status TEXT);
          CREATE TABLE inbox_items(id TEXT,thread_id TEXT,title TEXT);
          CREATE TABLE thread_timeline_ledger(host_id TEXT,thread_id TEXT,sequence INTEGER);
        ''')
        return c

    def definition(self, aid, target, prompt='hello'):
        path = self.home/'automations'/aid
        path.mkdir(parents=True)
        (path/'automation.toml').write_text(f'id = "{aid}"\ntarget_thread_id = "{target}"\nprompt = "{prompt}"\nstatus = "ACTIVE"\n', encoding='utf-8')
        (path/'memory.md').write_text('schedule context', encoding='utf-8')

    def test_schedule_union_and_disagreement(self):
        c = self.db()
        c.executemany('INSERT INTO automations VALUES (?,?,?,?,?)', [('toml', OTHER,'hello','ACTIVE',None), ('db',SID,'hello','ACTIVE',None), ('run',OTHER,'hello','ACTIVE',None), ('unrelated',OTHER,'hello','ACTIVE',None)])
        c.execute('INSERT INTO automation_runs VALUES (?,?,?)',(SID,'run','PENDING'))
        c.commit(); c.close()
        self.definition('toml', SID)
        self.definition('db', SID)
        self.definition('run', OTHER)
        self.definition('unrelated', OTHER)
        result = dep.collect(self.home, {SID})
        self.assertEqual(result['automation_ids'], ['db','run','toml'])
        self.assertEqual(len(result['records']['sqlite/codex-dev.db']['automations']), 3)
        self.assertEqual(len(result['files']), 6)
        self.assertTrue(any('behavior differs' in b for b in result['blockers']))
        self.assertTrue(any('requires target session' in b for b in result['blockers']))

    def test_only_session_owned_memory_captured(self):
        p = self.home/('memories/'+SID); p.mkdir(parents=True)
        (p/'context.md').write_text('shared context', encoding='utf-8')
        result = dep.collect(self.home,{SID})
        self.assertEqual(result['files'][0]['path'], 'memories/'+SID+'/context.md')
        self.assertEqual(result['files'][0]['kind'], 'text')
        self.assertIn('unowned shared memory',result['notes'][0])

    def test_credential_files_are_not_dependency_payloads(self):
        p=self.home/'memories'/SID;p.mkdir(parents=True)
        (p/'auth.json').write_text('{}')
        (p/'.env').write_text('TOKEN=fixture')
        result=dep.collect(self.home,{SID})
        self.assertEqual(result['files'],[])
        self.assertEqual(len(result['blockers']),2)

    def test_global_state_selective_merge_and_drafts(self):
        state = {'pinned-thread-ids':[SID,OTHER], 'thread-project-assignments':{SID:{'projectId':'p'},OTHER:{'projectId':'q'}},
                 'local-projects':{'p':{'id':'p','rootPaths':['C:/code']},'q':{'id':'q'}},'project-order':['p','q'],
                 'electron-persisted-atom-state':{'thread-client-id-v1:local%3A'+SID:'client:x',
                     'composer-prompt-drafts-v2':{'client:x':{'text':'draft'},'client:y':{'text':'other'}},
                     'thread-descriptions-v1':{SID:'selected',OTHER:'other'}},'unrelated':True}
        (self.home/'.codex-global-state.json').write_text(json.dumps(state), encoding='utf-8')
        result=dep.collect(self.home,{SID})
        self.assertEqual(result['global_state']['pinned-thread-ids'],[SID])
        dest=Path(self.temp.name)/'dest';dest.mkdir()
        (dest/'.codex-global-state.json').write_text(json.dumps({'unrelated':True,'pinned-thread-ids':[OTHER],'thread-project-assignments':{OTHER:{'projectId':'q'}}}),encoding='utf-8')
        prepared=dep.prepare(result,dest,[],lambda v,m:v,{})
        merged=json.loads(prepared['files'][0]['data'])
        self.assertTrue(merged['unrelated'])
        self.assertEqual(merged['pinned-thread-ids'],[OTHER,SID])
        self.assertIn(OTHER,merged['thread-project-assignments'])
        self.assertEqual(merged['electron-persisted-atom-state']['composer-prompt-drafts-v2'],{'client:x':{'text':'draft'}})

    def test_identity_binding_requires_explicit_mapping(self):
        c=self.db();c.execute('INSERT INTO thread_timeline_ledger VALUES (?,?,?)',('old-host',SID,1));c.commit();c.close()
        result=dep.collect(self.home,{SID})
        blocked=dep.prepare(result,self.home,[],lambda v,m:v,{})
        self.assertTrue(any('Unresolved destination binding' in b for b in blocked['blockers']))
        prepared=dep.prepare(result,self.home,[],lambda v,m:v,{'old-host':'new-host'})
        self.assertFalse(prepared['blockers'])
        self.assertEqual(prepared['records']['sqlite/codex-dev.db']['thread_timeline_ledger'][0]['host_id'],'new-host')

    def test_active_schedule_status_preserved(self):
        c=self.db();c.execute('INSERT INTO automations VALUES (?,?,?,?,?)',('s',SID,'hello','ACTIVE','old-user'));c.commit();c.close()
        self.definition('s',SID)
        result=dep.collect(self.home,{SID})
        prepared=dep.prepare(result,self.home,[],lambda v,m:v,{'old-user':'new-user'})
        self.assertEqual(prepared['records']['sqlite/codex-dev.db']['automations'][0]['status'],'ACTIVE')
        self.assertFalse(prepared['blockers'])

    def test_equivalent_schedule_json_and_toml_directories(self):
        c=self.db()
        c.execute('ALTER TABLE automations ADD COLUMN cwds TEXT')
        c.execute('INSERT INTO automations VALUES (?,?,?,?,?,?)',('s',SID,'hello','ACTIVE',None,'["C:/project"]'))
        c.commit();c.close()
        self.definition('s',SID)
        path=self.home/'automations/s/automation.toml'
        with path.open('a',encoding='utf-8') as out:out.write('cwds = ["C:/project"]\n')
        self.assertEqual(dep.collect(self.home,{SID})['blockers'],[])

    def test_unknown_session_state_is_reported(self):
        (self.home/'.codex-global-state.json').write_text(json.dumps({'future-store':{SID:{'x':1}}}),encoding='utf-8')
        result=dep.collect(self.home,{SID})
        self.assertTrue(any('Unsupported session-linked' in b for b in result['blockers']))


if __name__ == '__main__':
    unittest.main()

import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid
import zipfile

import session_clone as clone
import session_transfer as transfer
import test_session_transfer as fixtures

SID, CHILD = fixtures.SID, fixtures.CHILD


class CloneTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TransferTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_clone_roundtrip_preserves_source_and_rewrites_offsets(self):
        source = self.fixture.export()
        source_hash = transfer.file_sha(source)
        source_db_hash = transfer.file_sha(self.fixture.source/'state_5.sqlite')
        result = clone.clone_bundle(source, self.fixture.base/'clones')
        self.assertNotIn(result['session_id'], {SID, CHILD})
        z, m, records, indices = transfer.read_bundle(result['zip'], 10_000_000)
        with z:
            self.assertEqual(set(m['session_ids']), {result['identity_map'][SID], result['identity_map'][CHILD]})
            self.assertEqual(indices['session_index.jsonl'][0]['id'], result['session_id'])
            for row in records['thread_history_1.sqlite']['thread_turns']:
                path = 'files/codex/'+m['rollouts'][row['thread_id']]
                data = z.read(path)
                lines = data.splitlines(keepends=True)
                self.assertEqual(row['rollout_byte_offset'], len(lines[0]))
                self.assertEqual(row['rollout_end_byte_offset'], len(data))
                self.assertEqual(json.loads(lines[0])['payload']['id'], row['thread_id'])
                self.assertEqual(row['turn_id'], result['identity_map']['turn1'])
        self.assertEqual(source_hash, transfer.file_sha(source))
        self.assertEqual(source_db_hash, transfer.file_sha(self.fixture.source/'state_5.sqlite'))
        imported = self.fixture.imp(Path(result['zip']), session_id=result['session_id'], apply=True, offline_confirmed=True)
        self.assertEqual(imported['status'], 'imported')

    def test_no_clobber_and_invalid_clone_id(self):
        source = self.fixture.export()
        with self.assertRaisesRegex(ValueError, 'must differ'):
            clone.clone_bundle(source, self.fixture.base/'clones', new_session_id=SID)
        new = str(uuid.uuid4())
        result = clone.clone_bundle(source, self.fixture.base/'clones', new_session_id=new)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            clone.clone_bundle(source, self.fixture.base/'clones', new_session_id=new)
        self.assertEqual(result['sha256'], transfer.file_sha(Path(result['zip'])))

    def test_opaque_nested_json_and_identifier_boundaries(self):
        rewrite = clone.remapper({SID: 'new-id', 'turn1': 'new-turn'})
        obj = {'encrypted_content': SID, 'text': SID, 'payload': json.dumps({'encrypted_content': SID, 'thread_id': SID}),
               'ids': ['turn1', 'turn10'], 'path': 'sessions/'+SID+'.jsonl'}
        result = rewrite(obj)
        self.assertEqual(result['encrypted_content'], SID)
        self.assertEqual(json.loads(result['payload'])['encrypted_content'], SID)
        self.assertEqual(json.loads(result['payload'])['thread_id'], 'new-id')
        self.assertEqual(result['ids'], ['new-turn', 'turn10'])
        self.assertEqual(result['path'], 'sessions/new-id.jsonl')
        self.assertEqual(rewrite({'text': 'Discuss turn1 later', 'message': 'turn1'})['text'], 'Discuss turn1 later')
        self.assertEqual(rewrite({'message': 'turn1'})['message'], 'turn1')

    def test_encoded_ui_key_remaps_uuid_and_preserves_encoding(self):
        new = '44444444-4444-4444-8444-444444444444'
        rewrite = clone.remapper({SID: new})
        oldkey = 'thread-client-id-v1:local%3A'+SID
        result = rewrite({oldkey: {'route': 'local%3a'+SID+'%2Fdetails'}})
        self.assertEqual(result, {'thread-client-id-v1:local%3A'+new: {'route': 'local%3a'+new+'%2Fdetails'}})
        self.assertEqual(rewrite('prefixA'+SID), 'prefixA'+SID)
        self.assertEqual(rewrite('%41'+SID), '%41'+SID)
        self.assertEqual(rewrite(SID+'%41'), SID+'%41')

    def test_corrupt_archive_and_numeric_identity_fail_closed(self):
        source = self.fixture.export()
        with zipfile.ZipFile(source, 'a') as z:
            z.writestr('unlisted.txt', 'bad')
        with self.assertRaisesRegex(ValueError, 'Unlisted'):
            clone.clone_bundle(source, self.fixture.base/'clones')
        with self.assertRaisesRegex(ValueError, 'numeric relational'):
            clone.identity_maps({'session_ids': [SID], 'session_id': SID}, {'state_5.sqlite': {'queued_items': [{'id': 42, 'thread_id': SID}]}})

    def test_automation_and_ancillary_ids_have_consistent_mapping(self):
        records = {'sqlite/codex-dev.db': {'automations': [{'id': 'daily-summary', 'target_thread_id': SID}],
                                         'automation_runs': [{'id': 'run-1', 'automation_id': 'daily-summary', 'thread_id': SID}]},
                   'state_5.sqlite': {'thread_artifacts': [{'id': 'artifact-1', 'thread_id': SID}]}}
        mapping = clone.identity_maps({'session_ids': [SID], 'session_id': SID, 'supplemental': {'automation_ids': ['daily-summary']}}, records)
        changed = clone.remapper(mapping)(records)
        db = changed['sqlite/codex-dev.db']
        self.assertEqual(db['automations'][0]['id'], db['automation_runs'][0]['automation_id'])
        self.assertEqual(db['automations'][0]['target_thread_id'], mapping[SID])
        self.assertNotEqual(db['automation_runs'][0]['id'], 'run-1')


@unittest.skipUnless(os.environ.get('CODEX_CLONE_TEST_BINARY'), 'Set trusted CODEX_CLONE_TEST_BINARY for isolated native test')
class NativeFixtureTests(unittest.TestCase):
    def test_paginated_fork_and_full_native_visibility(self):
        with tempfile.TemporaryDirectory(prefix='codex-native-clone-test-') as temp:
            root = Path(temp).resolve()
            codex = root/'home'
            codex.mkdir()
            sid, turn = str(uuid.uuid4()), str(uuid.uuid4())
            ts = '2026-09-09T12:00:00.000Z'
            def rec(kind, payload):
                return {'timestamp': ts, 'type': kind, 'payload': payload}
            rows = [rec('session_meta', {'id': sid, 'session_id': sid, 'timestamp': ts, 'cwd': str(root),
                     'originator': 'codex_cli_rs', 'cli_version': '0.153.1', 'source': 'cli',
                     'model_provider': 'openai', 'history_mode': 'paginated', 'base_instructions': {'text': 'Fixture'}}),
                    rec('event_msg', {'type': 'task_started', 'turn_id': turn, 'model_context_window': 200000}),
                    rec('response_item', {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Fixture question'}]}),
                    rec('event_msg', {'type': 'item_completed', 'thread_id': sid, 'turn_id': turn,
                        'item': {'type': 'UserMessage', 'id': 'fixture-user', 'client_id': None,
                                 'content': [{'type': 'text', 'text': 'Fixture question', 'text_elements': []}]}}),
                    rec('response_item', {'type': 'message', 'role': 'assistant', 'phase': 'final_answer',
                                         'content': [{'type': 'output_text', 'text': 'Fixture answer'}]}),
                    rec('event_msg', {'type': 'item_completed', 'thread_id': sid, 'turn_id': turn,
                        'item': {'type': 'AgentMessage', 'id': 'fixture-agent', 'phase': 'final_answer',
                                 'content': [{'type': 'Text', 'text': 'Fixture answer'}]}}),
                    rec('event_msg', {'type': 'task_complete', 'turn_id': turn, 'last_agent_message': 'Fixture answer'})]
            path = codex/'sessions'/'2026'/'09'/'09'/('rollout-2026-09-09T12-00-00-'+sid+'.jsonl')
            path.parent.mkdir(parents=True)
            path.write_bytes(b''.join(transfer.dumps(dict(r, ordinal=i))+b'\n' for i, r in enumerate(rows)))
            before = transfer.file_sha(path)
            with clone.AppServer(os.environ['CODEX_CLONE_TEST_BINARY'], codex) as client:
                client.request('thread/list', {'limit': 100})
                client.request('thread/resume', {'threadId': sid, 'path': str(path), 'excludeTurns': True})
                report = client.verify(sid)
                self.assertEqual(report['turn_count'], 1)
                self.assertEqual(report['item_count'], 2)
                self.assertTrue(report['listed'])
                self.assertEqual(report['history_mode'], 'paginated')
                fork = client.fork(sid, path, root)
                self.assertNotEqual(fork['id'], sid)
                fork_turns = client.pages('thread/turns/list', {'threadId': fork['id'], 'itemsView': 'full', 'limit': 100})
                self.assertEqual(len(fork_turns), 1)
                self.assertEqual(len(fork_turns[0]['items']), 2)
            self.assertEqual(before, transfer.file_sha(path))


if __name__ == '__main__':
    unittest.main()

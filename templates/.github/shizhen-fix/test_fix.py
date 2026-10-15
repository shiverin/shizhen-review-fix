"""Behavioral boundary tests; no live keys, model calls, or remote writes."""

import base64
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.request
import zipfile


BASE = Path(__file__).resolve().parents[1]
TARGET = BASE / 'templates/.github/shizhen-fix/fix.py'
if not TARGET.exists():
    TARGET = Path(__file__).with_name('fix.py')
spec = importlib.util.spec_from_file_location('fix', TARGET)
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)
HEAD = 'a' * 40
FILE = 'src/main/java/example/Amount.java'
SOURCE = 'class Amount { int value = -1; }\n'


def pull(fork=False):
    return {'number': 7, 'user': {'id': fix.AUTHOR_ID, 'login': fix.AUTHOR_LOGIN},
            'state': 'open', 'draft': False, 'html_url': 'https://github.com/team/repo/pull/7',
            'head': {'sha': HEAD, 'ref': 'feature',
                     'repo': {'full_name': 'author/repo' if fork else 'team/repo'}},
            'base': {'ref': 'main'}}


class Boundaries(unittest.TestCase):
    def test_only_numeric_author_identity_is_trusted(self):
        pr = pull()
        pr['user']['id'] += 1
        with self.assertRaises(fix.Stop):
            fix.eligible(pr)

    def test_renaming_allowed_user_does_not_transfer_identity(self):
        pr = pull()
        pr['user']['login'] = 'renamed-owner'
        fix.eligible(pr)

    def test_closed_draft_missing_fork_and_fix_branches_are_rejected(self):
        for case in ['closed', 'draft', 'fork', 'branch']:
            pr = pull()
            if case == 'closed': pr['state'] = 'closed'
            if case == 'draft': pr['draft'] = True
            if case == 'fork': pr['head']['repo'] = None
            if case == 'branch': pr['head']['ref'] = 'shizhen-fix/pr-7-old'
            with self.subTest(case=case), self.assertRaises(fix.Stop):
                fix.eligible(pr)

    def test_immutable_sha_and_positive_number_validation(self):
        self.assertEqual(fix.require_number('38694141097'), 38694141097)
        for value in ['0', '-1', '2.1', '$(id)', '１２']:
            with self.assertRaises(fix.Stop): fix.require_number(value)
        for value in ['main', '../../secret', 'a' * 39, None]:
            with self.assertRaises(fix.Stop): fix.require_sha(value)

    def test_paths_cannot_escape_or_modify_automation(self):
        self.assertTrue(fix.allowed_path(FILE))
        for path in ['../x.java', '/src/main/java/A.java', 'src/main/java/../A.java',
                     '.github/workflows/review.yml', 'build.gradle', '.env',
                     'src/main/java/.git/x.java', 'src/main/java/evil\n.java',
                     'src//main/java/A.java', 'src\\main\\java\\A.java']:
            with self.subTest(path=path): self.assertFalse(fix.allowed_path(path))

    def test_exact_edit_changes_only_the_selected_substring(self):
        actual = fix.apply_edits([{'path': FILE, 'before': '-1', 'after': '0'}],
                                 {FILE: SOURCE}, {FILE})
        self.assertEqual(actual, {FILE: SOURCE.replace('-1', '0')})

    def test_ambiguous_missing_empty_and_unrelated_edits_are_rejected(self):
        for before in ['class', 'absent', '']:
            text = SOURCE + (' class' if before == 'class' else '')
            with self.assertRaises(fix.Stop):
                fix.apply_edits([{'path': FILE, 'before': before, 'after': 'other'}],
                                {FILE: text}, {FILE})
        with self.assertRaises(fix.Stop):
            fix.apply_edits([{'path': FILE, 'before': '-1', 'after': '0'}], {FILE: SOURCE}, set())

    def test_file_modes_reject_symlinks_and_executables(self):
        gh = Mock()
        for mode in ['120000', '100755', '160000']:
            gh._trees = {HEAD: {FILE: {'mode': mode, 'type': 'blob'}}}
            with self.assertRaises(fix.Stop): fix.file_at(gh, HEAD, FILE)
            gh.api.assert_not_called()

    def test_truncated_tree_is_rejected(self):
        gh = fix.GitHub('team/repo', 'fake')
        gh.api = Mock(side_effect=[{'tree': {'sha': 'b' * 40}}, {'truncated': True}])
        with self.assertRaises(fix.Stop): fix.file_at(gh, HEAD, FILE)

    def test_stale_proposal_stops_before_reading_source(self):
        gh = Mock(repository='team/repo')
        pr = pull(); pr['head']['sha'] = 'b' * 40
        gh.api.return_value = pr
        with self.assertRaises(fix.Stop):
            fix.validate_proposal(gh, {'repository': 'team/repo', 'pr_number': 7, 'head_sha': HEAD})
        self.assertEqual(gh.api.call_count, 1)

    def test_cross_repository_proposal_is_rejected(self):
        gh = Mock(repository='team/repo')
        with self.assertRaises(fix.Stop): fix.validate_proposal(gh, {'repository': 'evil/repo'})
        gh.api.assert_not_called()

    def test_redirect_strips_bearer_on_host_change(self):
        handler = fix.SafeRedirect()
        req = urllib.request.Request('https://api.github.com/artifact', headers={'Authorization': 'Bearer fake'})
        new = handler.redirect_request(req, None, 302, 'Found', {}, 'https://storage.example/archive')
        self.assertIsNone(new.get_header('Authorization'))
        same = handler.redirect_request(req, None, 302, 'Found', {}, 'https://api.github.com/next')
        self.assertEqual(same.get_header('Authorization'), 'Bearer fake')
        with self.assertRaises(fix.Stop):
            handler.redirect_request(req, None, 302, 'Found', {}, 'http://storage.example/archive')


class TriggerGuards(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.previous = Path.cwd()
        os.chdir(self.temporary.name)
        self.addCleanup(os.chdir, self.previous)
        self.environ = patch.dict(os.environ, {
            'GITHUB_EVENT_PATH': str(Path.cwd() / 'event.json'),
            'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_OUTPUT': str(Path.cwd() / 'output'),
            'GITHUB_STEP_SUMMARY': str(Path.cwd() / 'summary'),
        })
        self.environ.start(); self.addCleanup(self.environ.stop)
        Path('event.json').write_text(json.dumps({'inputs': {'pr_number': 7}}))

    def test_manual_run_cannot_bypass_author_restriction(self):
        gh = Mock(repository='team/repo')
        pr = pull(); pr['user']['id'] += 1; gh.api.return_value = pr
        with patch.object(fix, 'manual_handoff') as handoff, patch.object(fix, 'request_json') as model:
            with self.assertRaises(fix.Stop): fix.generate(gh)
            handoff.assert_not_called(); model.assert_not_called()

    def test_automatic_run_cannot_bypass_author_restriction(self):
        os.environ['GITHUB_EVENT_NAME'] = 'workflow_run'
        Path('event.json').write_text(json.dumps({'workflow_run': {'id': 123}}))
        gh = Mock(repository='team/repo'); pr = pull(); pr['user']['id'] += 1
        gh.api.return_value = pr
        with patch.object(fix, 'handoff_from_run', return_value={'pr_number': 7}), \
             patch.object(fix, 'request_json') as model:
            with self.assertRaises(fix.Stop): fix.generate(gh)
            model.assert_not_called()

    def test_accepted_fix_stops_repair_loop(self):
        gh = Mock(repository='team/repo'); gh.api.return_value = pull()
        gh.pages.return_value = [{'commit': {'message': 'Apply shizhen-fix for PR #7'}}]
        with patch.object(fix, 'manual_handoff', return_value={'pr_number': 7, 'head_sha': HEAD}), \
             patch.object(fix, 'request_json') as model:
            with self.assertRaises(fix.Stop): fix.generate(gh)
            model.assert_not_called()

    def test_atomic_reservation_blocks_duplicate_model_calls(self):
        gh = Mock(repository='team/repo')
        gh.api.side_effect = [pull(), pull(), fix.Stop('API request failed with HTTP 422.'),
                              {'object': {'sha': HEAD}}]
        gh.pages.side_effect = [[], [{'filename': FILE, 'status': 'modified'}]]
        data = {'pr_number': 7, 'head_sha': HEAD,
                'review': {'review': {'key_issues_to_review': [{'issue': 'bad input'}]}}}
        with patch.object(fix, 'manual_handoff', return_value=data), \
             patch.object(fix, 'file_at', return_value=SOURCE), patch.object(fix, 'request_json') as model, \
             patch.dict(os.environ, {'LLM_API_KEY': 'fake-not-sent'}):
            with self.assertRaises(fix.Stop): fix.generate(gh)
            model.assert_not_called()
        self.assertEqual(gh.api.call_count, 4)

    def test_handoff_rejects_wrong_workflow_without_downloading_artifacts(self):
        gh = Mock(repository='team/repo')
        gh.api.return_value = {'path': '.github/workflows/other.yml', 'name': 'shizhen-review'}
        with patch.object(fix, 'open_request') as download:
            with self.assertRaises(fix.Stop): fix.handoff_from_run(gh, 123)
            download.assert_not_called()

    def test_handoff_binds_archive_to_the_source_run(self):
        gh = Mock(repository='team/repo', token='fake', prefix='https://api.github.com/repos/team/repo/')
        run = {'path': '.github/workflows/shizhen-review.yml', 'name': 'shizhen-review',
               'conclusion': 'success', 'event': 'pull_request_target',
               'repository': {'full_name': 'team/repo'}}
        gh.api.side_effect = [run, {'artifacts': [{'id': 1, 'name': 'shizhen-review-handoff-1'}]}]
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('handoff.json', json.dumps({'repository': 'team/repo', 'run_id': 999,
                                                      'run_attempt': 1}))
        with patch.object(fix, 'open_request', return_value=io.BytesIO(archive.getvalue())):
            with self.assertRaises(fix.Stop): fix.handoff_from_run(gh, 123)

    def test_run_without_eligible_author_handoff_is_a_clean_skip(self):
        gh = Mock(repository='team/repo')
        gh.api.side_effect = [
            {'path': '.github/workflows/shizhen-review.yml', 'name': 'shizhen-review',
             'conclusion': 'success', 'event': 'pull_request_target',
             'repository': {'full_name': 'team/repo'}, 'run_attempt': 1},
            {'artifacts': []},
        ]
        with self.assertRaisesRegex(fix.Stop, '^Skipped:'):
            fix.handoff_from_run(gh, 123)

    def test_no_findings_reserves_no_branch_and_spends_no_model_call(self):
        gh = Mock(repository='team/repo'); gh.api.return_value = pull()
        gh.pages.return_value = []
        review = {'pr_number': 7, 'head_sha': HEAD,
                  'review': {'review': {'key_issues_to_review': []}}}
        with patch.object(fix, 'manual_handoff', return_value=review), \
             patch.object(fix, 'request_json') as model:
            with self.assertRaisesRegex(fix.Stop, '^No actionable'): fix.generate(gh)
            model.assert_not_called()
        self.assertEqual(gh.api.call_count, 2)

    def test_materialization_rejects_symlinks_and_traversal(self):
        for malicious in ['symlink', 'traversal']:
            raw = io.BytesIO()
            with tarfile.open(fileobj=raw, mode='w:gz') as archive:
                entry = tarfile.TarInfo('root/link' if malicious == 'symlink' else 'root/../../outside')
                if malicious == 'symlink':
                    entry.type = tarfile.SYMTYPE; entry.linkname = '/tmp/outside'
                archive.addfile(entry, io.BytesIO())
            Path('proposal.json').write_text(json.dumps({'head_sha': HEAD}))
            gh = Mock(prefix='https://api.github.com/repos/team/repo/', token='fake')
            with patch.object(fix, 'validate_proposal', return_value=(pull(), {})), \
                 patch.object(fix, 'open_request', return_value=io.BytesIO(raw.getvalue())):
                with self.subTest(case=malicious), self.assertRaises(fix.Stop): fix.materialize(gh)
            Path('candidate').rmdir()

    def test_publication_is_draft_only_and_does_not_edit_original_branch(self):
        for fork in [False, True]:
            pr = pull(fork=fork)
            proposal = {'pr_number': 7, 'head_sha': HEAD, 'branch': 'shizhen-fix/pr-7-' + HEAD[:12],
                        'decisions': [{'finding': 1, 'decision': 'fix', 'reason': 'Reject negative values.'}]}
            Path('proposal.json').write_text(json.dumps(proposal))
            gh = Mock(repository='team/repo')
            def api(path, data=None, method=None):
                if path.startswith('git/ref/'): return {'object': {'sha': HEAD}}
                if path.startswith('git/commits/') and data is None: return {'tree': {'sha': 'b' * 40}}
                if path == 'git/blobs': return {'sha': 'c' * 40}
                if path == 'git/trees': return {'sha': 'd' * 40}
                if path == 'git/commits': return {'sha': 'e' * 40}
                if path.startswith('git/refs/'): return {}
                if path == 'pulls': return {'html_url': 'https://github.com/team/repo/pull/8'}
                self.fail('Unexpected API operation: ' + path)
            gh.api.side_effect = api
            with patch.object(fix, 'validate_proposal', return_value=(pr, {FILE: SOURCE})), \
                 patch.dict(os.environ, {'GITHUB_RUN_ID': '123', 'VALIDATION_RESULT': 'failure'}):
                fix.publish(gh)
            created = [c for c in gh.api.call_args_list if c.args[0] == 'pulls'][0].args[1]
            self.assertIs(created['draft'], True)
            self.assertEqual(created['base'], 'main' if fork else 'feature')
            self.assertIn('**failure**', created['body'])
            writes = [c.args[0] for c in gh.api.call_args_list if len(c.args) > 1]
            self.assertFalse(any('/feature' in p or 'merge' in p or 'reviews' in p for p in writes))

    def test_generate_validate_and_materialize_one_supported_repair(self):
        gh = Mock(repository='team/repo', prefix='https://api.github.com/repos/team/repo/', token='fake')
        gh.api.return_value = pull()
        gh.pages.side_effect = [[], [{'filename': FILE, 'status': 'modified'}]]
        review = {'pr_number': 7, 'head_sha': HEAD, 'run_id': 123,
                  'review': {'review': {'key_issues_to_review': [{'issue': 'negative value'}]}}}
        plan = {'decisions': [{'finding': 1, 'decision': 'fix', 'reason': 'Reject negative default.'}],
                'edits': [{'path': FILE, 'before': '-1', 'after': '0'}]}
        reply = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(plan)}}]}
        with patch.object(fix, 'manual_handoff', return_value=review), \
             patch.object(fix, 'file_at', return_value=SOURCE), \
             patch.object(fix, 'request_json', return_value=reply) as model, \
             patch.dict(os.environ, {'LLM_API_KEY': 'fake-not-sent'}):
            fix.generate(gh)
        self.assertIn('proposed=true', Path('output').read_text())
        sent = model.call_args.args[2]
        self.assertEqual(sent['model'], 'x-test-1')
        self.assertEqual(sent['reasoning_effort'], 'high')
        self.assertNotIn('fake-not-sent', json.dumps(sent))
        proposal = json.loads(Path('proposal.json').read_text())
        gh.pages.side_effect = None
        gh.pages.return_value = [{'filename': FILE, 'status': 'modified'}]
        with patch.object(fix, 'file_at', return_value=SOURCE):
            pr, updated = fix.validate_proposal(gh, proposal)
        self.assertEqual(updated[FILE], SOURCE.replace('-1', '0'))
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode='w:gz') as archive:
            entry = tarfile.TarInfo('snapshot/' + FILE)
            entry.size = len(SOURCE.encode())
            archive.addfile(entry, io.BytesIO(SOURCE.encode()))
        with patch.object(fix, 'validate_proposal', return_value=(pr, updated)), \
             patch.object(fix, 'open_request', return_value=io.BytesIO(raw.getvalue())):
            fix.materialize(gh)
        self.assertEqual((Path('candidate') / FILE).read_text(), updated[FILE])

    def test_incomplete_model_response_never_publishes_a_proposal(self):
        gh = Mock(repository='team/repo'); gh.api.return_value = pull()
        gh.pages.side_effect = [[], [{'filename': FILE, 'status': 'modified'}]]
        review = {'pr_number': 7, 'head_sha': HEAD, 'run_id': 123,
                  'review': {'review': {'key_issues_to_review': [{'issue': 'negative value'}]}}}
        reply = {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}
        with patch.object(fix, 'manual_handoff', return_value=review), \
             patch.object(fix, 'file_at', return_value=SOURCE), \
             patch.object(fix, 'request_json', return_value=reply), \
             patch.dict(os.environ, {'LLM_API_KEY': 'fake-not-sent'}):
            with self.assertRaises(fix.Stop): fix.generate(gh)
        self.assertFalse(Path('proposal.json').exists())


if __name__ == '__main__':
    unittest.main()

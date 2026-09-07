import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SHARED = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, SHARED / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


scope, gate = module('review_scope'), module('review_gate')


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.hooksPath', str(self.root / 'no-hooks'))
        for name in ('committed.txt', 'staged.txt', 'unstaged.txt', 'unrelated.txt', 'deleted.txt'):
            (self.repo / name).write_text('before\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.base = self.git('rev-parse', 'HEAD').decode().strip()
        (self.repo / 'committed.txt').write_text('committed change\n')
        self.git('add', 'committed.txt')
        self.git('commit', '-qm', 'task')

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE)

    def capture(self, names):
        return scope.capture(self.repo, self.base, names)

    def test_clean_committed_branch(self):
        packet, patch, _ = self.capture(['committed.txt'])
        self.assertIn(b'+committed change', patch)
        self.assertNotEqual(packet['base'], packet['head'])

    def test_mixed_scope_excludes_unrelated_and_preserves_index(self):
        (self.repo / 'staged.txt').write_text('staged change\n')
        self.git('add', 'staged.txt')
        (self.repo / 'unstaged.txt').write_text('unstaged change\n')
        (self.repo / 'untracked.txt').write_text('new file\n')
        (self.repo / 'unrelated.txt').write_text('private unrelated work\n')
        before = self.git('diff', '--cached', '--binary')
        names = ['committed.txt', 'staged.txt', 'unstaged.txt', 'untracked.txt']
        packet, patch, blobs = self.capture(names)
        self.assertEqual({f['path'] for f in packet['files']}, set(names))
        for value in (b'+committed change', b'+staged change', b'+unstaged change'):
            self.assertIn(value, patch)
        self.assertEqual(list(blobs.values()), [b'new file\n'])
        self.assertNotIn(b'private unrelated', patch)
        self.assertEqual(before, self.git('diff', '--cached', '--binary'))

    def test_staged_overridden_content_is_final_content(self):
        (self.repo / 'staged.txt').write_text('intermediate\n')
        self.git('add', 'staged.txt')
        (self.repo / 'staged.txt').write_text('final\n')
        _, patch, _ = self.capture(['staged.txt'])
        self.assertIn(b'+final', patch)
        self.assertNotIn(b'intermediate', patch)

    def test_filename_safety(self):
        names = ['space name.txt', 'line\nbreak.txt', ':(glob)*', '-dash.txt']
        for name in names:
            (self.repo / name).write_text(name)
        packet, _, blobs = self.capture(names)
        self.assertEqual({f['path'] for f in packet['files']}, set(names))
        self.assertEqual(len(blobs), 4)
        self.git('--literal-pathspecs', 'add', '--', *names)
        tracked, patch, blobs = self.capture(names)
        self.assertEqual({f['path'] for f in tracked['files']}, set(names))
        self.assertTrue(all(not f['untracked'] for f in tracked['files']))
        self.assertFalse(blobs)
        self.assertEqual(patch.count(b'diff --git '), 4)

    def test_deletion_and_rename_sides(self):
        (self.repo / 'deleted.txt').rename(self.repo / 'renamed.txt')
        packet, patch, blobs = self.capture(['deleted.txt', 'renamed.txt'])
        self.assertEqual(packet['files'][0]['kind'], 'deleted')
        self.assertIn(b'deleted file mode', patch)
        self.assertEqual(list(blobs.values()), [b'before\n'])

    def test_drift_and_mode_change_invalidate_snapshot(self):
        first = self.capture(['committed.txt'])[0]['snapshot_id']
        (self.repo / 'committed.txt').write_text('later\n')
        second = self.capture(['committed.txt'])[0]['snapshot_id']
        self.assertNotEqual(first, second)
        (self.repo / 'committed.txt').chmod(0o755)
        self.assertNotEqual(second, self.capture(['committed.txt'])[0]['snapshot_id'])

    def test_symlink_does_not_copy_external_contents(self):
        private = self.root / 'private.txt'
        private.write_text('do not copy me')
        (self.repo / 'link').symlink_to(private)
        packet, patch, blobs = self.capture(['link'])
        self.assertEqual(packet['files'][0]['kind'], 'symlink')
        self.assertFalse(blobs)
        self.assertNotIn(b'do not copy me', patch)

    def test_invalid_scope_fails(self):
        for names in ([], ['../private'], ['/etc/hosts'], ['.git/config'], ['missing'], ['committed.txt'] * 2):
            with self.subTest(names=names), self.assertRaises(ValueError):
                self.capture(names)

    def test_cli_artifacts_and_repeatable_snapshot(self):
        paths = self.root / 'paths.json'
        paths.write_text('["committed.txt"]')
        ids = []
        for suffix in ('one', 'two'):
            output = self.root / suffix
            result = subprocess.run([sys.executable, str(SHARED / 'scripts/review_scope.py'), '--repo', str(self.repo), '--base-ref', self.base, '--paths-file', str(paths), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            ids.append(json.loads((output / 'scope.json').read_text())['snapshot_id'])
        self.assertEqual(ids[0], ids[1])

    @unittest.skipUnless(os.name == 'posix', 'requires POSIX permission bits')
    def test_cli_artifacts_are_private_under_permissive_umasks(self):
        (self.repo / 'untracked.txt').write_text('private source fixture\n')
        paths = self.root / 'paths.json'
        paths.write_text('["committed.txt", "untracked.txt"]')
        for mask in (0o000, 0o022, 0o077):
            with self.subTest(umask=oct(mask)):
                output = self.root / ('snapshot-' + str(mask))
                previous = os.umask(mask)
                try:
                    result = subprocess.run([sys.executable, str(SHARED / 'scripts/review_scope.py'), '--repo', str(self.repo), '--base-ref', self.base, '--paths-file', str(paths), '--output', str(output)], capture_output=True, text=True)
                finally:
                    os.umask(previous)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((output / 'untracked').stat().st_mode), 0o700)
                artifacts = [output / 'scope.json', output / 'changes.patch', *list((output / 'untracked').iterdir())]
                self.assertEqual(len(artifacts), 3)
                for artifact in artifacts:
                    self.assertEqual(stat.S_IMODE(artifact.stat().st_mode), 0o600, str(artifact))


class GitIsolationTests(unittest.TestCase):
    def test_fixture_ignores_contributor_signing_and_hooks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hooks = root / 'hooks'
            hooks.mkdir()
            hook = hooks / 'pre-commit'
            hook.write_text('#!/bin/sh\nexit 91\n')
            hook.chmod(0o755)
            config = root / 'global.gitconfig'
            config.write_text('[commit]\n\tgpgSign = true\n[gpg]\n\tprogram = '
                              + json.dumps(str(root / 'missing-signer'))
                              + '\n[core]\n\thooksPath = ' + json.dumps(str(hooks)) + '\n')
            with mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(config), 'GIT_CONFIG_NOSYSTEM': '1'}):
                fixture = ScopeTests('test_clean_committed_branch')
                try:
                    fixture.setUp()
                    fixture.test_clean_committed_branch()
                finally:
                    if hasattr(fixture, 'temp'):
                        fixture.tearDown()


class GateTests(unittest.TestCase):
    def setUp(self):
        self.expected = {'snapshot_id': 'current', 'jobs': {'risk': ['security', 'data-integrity']},
                         'checks': {'status': 'passed', 'evidence': ['Focused tests passed']}, 'execution_gaps': []}
        self.result = {'job': 'risk', 'snapshot_id': 'current', 'complete': True, 'coverage': {
            source: {'complete': True, 'evidence': ['Inspected /repo/api.py:1 and its caller'], 'limitations': []}
            for source in self.expected['jobs']['risk']}, 'findings': [], 'strengths': [], 'limitations': []}

    def status(self, results=None):
        return gate.evaluate(self.expected, [self.result] if results is None else results)['status']

    def test_complete_empty_review_passes(self):
        self.assertEqual(self.status(), 'REVIEW_PASSED')

    def test_missing_job_blocks(self):
        self.assertEqual(self.status([]), 'REVIEW_INCOMPLETE')

    def test_partial_source_blocks(self):
        del self.result['coverage']['data-integrity']
        self.assertEqual(self.status(), 'REVIEW_INCOMPLETE')

    def test_incomplete_and_unsupported_coverage_block(self):
        for field, value in [('complete', False), ('evidence', [])]:
            original = copy.deepcopy(self.result)
            self.result['coverage']['security'][field] = value
            self.assertEqual(self.status(), 'REVIEW_INCOMPLETE')
            self.result = original

    def test_stale_or_duplicate_results_block(self):
        self.assertEqual(self.status([self.result, self.result]), 'REVIEW_INCOMPLETE')
        self.result['snapshot_id'] = 'pre-fix'
        self.assertEqual(self.status(), 'REVIEW_INCOMPLETE')

    def test_malformed_results_block(self):
        for value in (None, [], 'APPROVED', {'complete': True}, {**self.result, 'complete': 'true'}, {**self.result, 'findings': None}):
            with self.subTest(value=value):
                self.assertEqual(self.status([value]), 'REVIEW_INCOMPLETE')

    def test_all_blockers_survive_more_than_five(self):
        self.result['findings'] = [{'sources': ['security'], 'severity': 'high', 'blocking': False,
            'title': 'Issue ' + str(i), 'file': '/repo/api.py', 'line': i + 1,
            'evidence': 'Concrete unsafe flow', 'recommendation': 'Check tenant ownership'} for i in range(9)]
        report = gate.evaluate(self.expected, [self.result])
        self.assertEqual(report['status'], 'FINDINGS_OPEN')
        self.assertEqual(report['blocking_findings'], 9)
        self.assertEqual(len(report['findings']), 9)

    def test_valid_blocker_survives_malformed_siblings(self):
        finding = {'sources': ['security'], 'severity': 'critical', 'blocking': True,
                   'title': 'Missing tenant boundary', 'file': '/repo/api.py', 'line': 1,
                   'evidence': 'Request selects another tenant', 'recommendation': 'Scope lookup to tenant'}
        self.result['findings'] = [None, finding, {'severity': 'high'}]
        report = gate.evaluate(self.expected, [self.result])
        self.assertEqual(report['status'], 'REVIEW_INCOMPLETE')
        self.assertEqual(report['findings'], [finding])
        self.assertEqual(report['blocking_findings'], 1)
        self.assertTrue(any('finding[0]' in gap for gap in report['gaps']))
        self.assertTrue(any('finding[2]' in gap for gap in report['gaps']))

    def test_partial_coverage_does_not_hide_valid_findings(self):
        finding = {'sources': ['security'], 'severity': 'critical', 'blocking': True,
                   'title': 'Missing tenant boundary', 'file': '/repo/api.py', 'line': 1,
                   'evidence': 'Request selects another tenant', 'recommendation': 'Scope lookup to tenant'}
        self.result['findings'] = [finding]
        del self.result['coverage']['data-integrity']
        self.result['strengths'] = None
        report = gate.evaluate(self.expected, [self.result])
        self.assertEqual(report['status'], 'REVIEW_INCOMPLETE')
        self.assertEqual(report['findings'], [finding])

    def test_execution_and_required_check_gaps_block(self):
        for reason in ('risk timed out', 'required model unavailable', 'reviewer modified files'):
            self.expected['execution_gaps'] = [reason]
            self.assertEqual(self.status(), 'REVIEW_INCOMPLETE')
        self.expected['execution_gaps'] = []
        self.expected['checks']['status'] = 'failed'
        self.assertEqual(self.status(), 'FINDINGS_OPEN')
        self.expected['checks']['status'] = 'incomplete'
        self.assertEqual(self.status(), 'REVIEW_INCOMPLETE')

    def test_invalid_expectations_never_pass(self):
        for expected in (None, {}, {**self.expected, 'jobs': {}}, {**self.expected, 'execution_gaps': None}):
            self.assertEqual(gate.evaluate(expected, [self.result])['status'], 'REVIEW_INCOMPLETE')

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"complete":false,"complete":true}', object_pairs_hook=gate.unique_object)

    def test_cli_exit_status_and_missing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected, result = root / 'expected.json', root / 'result.json'
            expected.write_text(json.dumps(self.expected))
            result.write_text(json.dumps(self.result))
            command = [sys.executable, str(SHARED / 'scripts/review_gate.py'), '--expected', str(expected), '--results']
            completed = subprocess.run(command + [str(result)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)['status'], 'REVIEW_PASSED')
            incomplete = subprocess.run(command + [str(root / 'missing.json')], capture_output=True, text=True)
            self.assertEqual(incomplete.returncode, 2, incomplete.stderr)
            self.assertEqual(json.loads(incomplete.stdout)['status'], 'REVIEW_INCOMPLETE')


if __name__ == '__main__':
    unittest.main(verbosity=2)

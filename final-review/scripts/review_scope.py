#!/usr/bin/env python3
"""Snapshot explicitly owned Git changes. Python 3.9+, standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(
        ['git', '-C', str(repo), *args],
        env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_LITERAL_PATHSPECS': '1'},
        stderr=subprocess.PIPE,
    )


def capture(repo, base_ref, names):
    repo = Path(repo).resolve(strict=True)
    root = Path(os.fsdecode(git(repo, 'rev-parse', '--show-toplevel')).rstrip('\n')).resolve()
    if root != repo:
        raise ValueError('--repo must be the repository root')
    if not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names):
        raise ValueError('paths-file must contain a nonempty JSON array of filenames')
    if len(set(names)) != len(names):
        raise ValueError('duplicate scope paths')
    for name in names:
        parts = PurePosixPath(name).parts
        if not name or '\0' in name or name.startswith('/') or '..' in parts or '.git' in parts:
            raise ValueError('invalid repository-relative filename: ' + repr(name))
        if str(PurePosixPath(name)) != name or name == '.':
            raise ValueError('scope paths must be normalized exact filenames')
        parent = (repo / name).parent.resolve()
        if parent != repo and repo not in parent.parents:
            raise ValueError('scope path traverses a symlink outside the repository')
    base = git(repo, 'rev-parse', '--verify', '--end-of-options', base_ref + '^{commit}').decode().strip()
    head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    if git(repo, 'ls-files', '-u', '-z'):
        raise ValueError('unmerged index: resolve or isolate the review scope first')
    changed = set(os.fsdecode(n) for n in git(repo, 'diff', '--name-only', '-z', '--no-renames', base, '--').split(b'\0') if n)
    untracked = set(os.fsdecode(n) for n in git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if n)
    if not set(names) <= changed | untracked:
        raise ValueError('selected filenames are unchanged, ignored, or unknown: ' + repr(sorted(set(names) - changed - untracked)))
    patch = git(repo, 'diff', '--no-ext-diff', '--no-textconv', '--binary', '--no-renames', base, '--', *sorted(names))
    files, payloads = [], {}
    for index, name in enumerate(sorted(names)):
        path = repo / name
        entry = {'path': name, 'untracked': name in untracked}
        try:
            info = path.lstat()
        except FileNotFoundError:
            entry.update(kind='deleted', mode=None, sha256=None)
        else:
            entry['mode'] = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                # Capture the link itself; never dereference possibly private external content.
                content = os.fsencode(os.readlink(path))
                entry.update(kind='symlink', target=os.fsdecode(content), sha256=digest(content))
            elif stat.S_ISREG(info.st_mode):
                content = path.read_bytes()
                entry.update(kind='file', sha256=digest(content))
                if name in untracked:
                    artifact = 'untracked/{:04d}.bin'.format(index)
                    entry['artifact'] = artifact
                    payloads[artifact] = content
            else:
                raise ValueError('unsupported scope entry (directory/submodule/special file): ' + repr(name))
        files.append(entry)
    scope = {'version': 1, 'repo': str(repo), 'base': base, 'head': head,
             'files': files, 'patch_sha256': digest(patch)}
    scope['snapshot_id'] = digest(json.dumps(scope, sort_keys=True, ensure_ascii=True).encode())
    return scope, patch, payloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--base-ref', required=True)
    parser.add_argument('--paths-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        repo = Path(args.repo).resolve()
        if output == repo or repo in output.parents:
            raise ValueError('review artifacts must be outside the target repository')
        names = json.loads(args.paths_file.read_text())
        snapshot = capture(repo, args.base_ref, names)
        # Catch concurrent changes during capture instead of certifying an inconsistent packet.
        if snapshot != capture(repo, args.base_ref, names):
            raise ValueError('scope changed during snapshot; retry once the worktree is stable')
        scope, patch, payloads = snapshot
        output.mkdir(parents=True, exist_ok=False)
        (output / 'changes.patch').write_bytes(patch)
        for name, data in payloads.items():
            destination = output / name
            destination.parent.mkdir(exist_ok=True)
            destination.write_bytes(data)
        (output / 'scope.json').write_text(json.dumps(scope, indent=2, ensure_ascii=True) + '\n')
        print(json.dumps({'snapshot_id': scope['snapshot_id'], 'scope': str(output / 'scope.json')}))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'status': 'REVIEW_INCOMPLETE', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

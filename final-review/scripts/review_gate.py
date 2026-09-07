#!/usr/bin/env python3
"""Fail closed on incomplete review results. Does not evaluate reviewer judgment."""
import argparse
import json
from pathlib import Path

SOURCES = {'pr-review', 'structural-quality', 'techdebt', 'security', 'regression',
           'performance', 'data-integrity', 'react-native'}
SEVERITIES = {'critical', 'high', 'medium', 'low', 'info'}


def strings(value, nonempty=False):
    return (isinstance(value, list) and (bool(value) or not nonempty)
            and all(isinstance(item, str) and item.strip() for item in value))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_finding(finding, sources):
    require(isinstance(finding, dict), 'malformed finding')
    require(strings(finding.get('sources'), True) and set(finding['sources']) <= set(sources), 'invalid finding sources')
    require(isinstance(finding.get('severity'), str) and finding['severity'] in SEVERITIES, 'invalid severity')
    require(type(finding.get('blocking')) is bool, 'missing blocking flag')
    require(all(isinstance(finding.get(k), str) and finding[k].strip() for k in ('title', 'file', 'evidence', 'recommendation')), 'missing finding evidence')
    require(Path(finding['file']).is_absolute() and type(finding.get('line')) is int and finding['line'] > 0, 'invalid file/line')


def validate_result(result, expected):
    require(isinstance(result, dict), 'result must be an object')
    job = result.get('job')
    require(isinstance(job, str) and job in expected['jobs'], 'unexpected/missing job')
    require(result.get('snapshot_id') == expected['snapshot_id'], job + ': stale snapshot')
    gaps = []
    if result.get('complete') is not True:
        gaps.append(job + ': incomplete or malformed completion status')
    sources = expected['jobs'][job]
    coverage = result.get('coverage')
    if not isinstance(coverage, dict):
        gaps.append(job + ': malformed source coverage')
        coverage = {}
    if set(coverage) != set(sources):
        gaps.append(job + ': missing/extra source coverage')
    for source in sources:
        item = coverage.get(source)
        if (not isinstance(item, dict) or item.get('complete') is not True
                or not strings(item.get('evidence'), True) or not strings(item.get('limitations'))):
            gaps.append(job + '/' + source + ': incomplete, malformed or unsubstantiated coverage')
    if not strings(result.get('limitations')) or not strings(result.get('strengths')):
        gaps.append(job + ': malformed summary')
    raw_findings = result.get('findings')
    findings = []
    if not isinstance(raw_findings, list):
        gaps.append(job + ': findings must be an array')
    else:
        # Preserve useful findings even when a sibling or coverage field is malformed.
        for index, finding in enumerate(raw_findings):
            try:
                validate_finding(finding, sources)
                findings.append(finding)
            except ValueError as exc:
                gaps.append('{}: finding[{}]: {}'.format(job, index, exc))
    return job, gaps, findings


def evaluate(expected, results, read_errors=()):
    try:
        require(isinstance(expected, dict), 'expectations must be an object')
        require(isinstance(expected.get('snapshot_id'), str) and expected['snapshot_id'].strip(), 'missing current snapshot')
        jobs = expected.get('jobs')
        require(isinstance(jobs, dict) and bool(jobs), 'expected job map must be nonempty')
        assigned = []
        for job, sources in jobs.items():
            require(isinstance(job, str) and job.strip() and strings(sources, True) and set(sources) <= SOURCES, 'invalid expected sources')
            assigned.extend(sources)
        require(len(set(assigned)) == len(assigned), 'sources assigned more than once')
        checks = expected.get('checks')
        require(isinstance(checks, dict) and isinstance(checks.get('status'), str) and checks['status'] in {'passed', 'not-required', 'failed', 'incomplete'}, 'missing check status')
        require(strings(checks.get('evidence'), True), 'missing check evidence/reason')
        require(strings(expected.get('execution_gaps')), 'missing execution gap record')
    except ValueError as exc:
        return {'status': 'REVIEW_INCOMPLETE', 'gaps': [str(exc)], 'findings': []}
    gaps, findings, seen = list(read_errors) + expected['execution_gaps'], [], set()
    if checks['status'] == 'incomplete':
        gaps.append('required checks incomplete')
    for result in results:
        try:
            job, result_gaps, result_findings = validate_result(result, expected)
            if job in seen:
                gaps.append(job + ': duplicate result')
            seen.add(job)
            gaps.extend(result_gaps)
            findings.extend(result_findings)
        except ValueError as exc:
            gaps.append(str(exc))
    gaps.extend(job + ': missing valid result' for job in jobs if job not in seen)
    blockers = [f for f in findings if f['blocking'] or f['severity'] in {'critical', 'high'}]
    status = 'REVIEW_INCOMPLETE' if gaps else ('FINDINGS_OPEN' if blockers or checks['status'] == 'failed' else 'REVIEW_PASSED')
    return {'status': status, 'gaps': gaps, 'blocking_findings': len(blockers),
            'checks': checks, 'findings': findings}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected', type=Path, required=True)
    parser.add_argument('--results', type=Path, nargs='*', default=[])
    args = parser.parse_args()
    try:
        expected = read_json(args.expected)
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'REVIEW_INCOMPLETE', 'gaps': [str(exc)]}))
        return 2
    results, errors = [], []
    for path in args.results:
        try:
            results.append(read_json(path))
        except (OSError, ValueError) as exc:
            errors.append(str(path) + ': ' + str(exc))
    report = evaluate(expected, results, errors)
    print(json.dumps(report, indent=2))
    return {'REVIEW_PASSED': 0, 'FINDINGS_OPEN': 1, 'REVIEW_INCOMPLETE': 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())

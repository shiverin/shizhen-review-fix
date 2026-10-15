"""Generate bounded review fixes without executing pull-request code."""

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parent
SETTINGS = json.loads((ROOT / 'config.json').read_text())
AUTHOR_ID = SETTINGS['author_id']  # Stable numeric identity, independent of display names.
AUTHOR_LOGIN = SETTINGS['author_login']
if type(AUTHOR_ID) is not int or AUTHOR_ID < 1:
    raise ValueError('Configure a positive GitHub author ID before enabling fixes.')
MODEL = 'x-test-1'
ENDPOINT = 'https://soclaas-api.comp.nus.edu.sg/v1/chat/completions'
SHA = re.compile(r'[0-9a-f]{40}')
MAX_FILE_BYTES = 60_000
MAX_PROPOSAL_BYTES = 500_000


class Stop(Exception):
    """An expected skip or a rejected, unsafe proposal."""


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Strip bearer credentials when GitHub redirects to artifact storage."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise Stop('Non-HTTPS redirects are not permitted.')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if (redirected is not None and urllib.parse.urlsplit(req.full_url).netloc
                != urllib.parse.urlsplit(newurl).netloc):
            redirected.remove_header('Authorization')
        return redirected


def open_request(request, timeout):
    return urllib.request.build_opener(SafeRedirect()).open(request, timeout=timeout)


def request_json(url, token, data=None, method=None):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json',
               'Content-Type': 'application/json', 'User-Agent': 'shizhen-fix'}
    request = urllib.request.Request(url, headers=headers, method=method,
                                     data=None if data is None else json.dumps(data).encode())
    try:
        with open_request(request, timeout=280 if url == ENDPOINT else 45) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise Stop('API response exceeded the size limit.')
        return json.loads(raw)
    except urllib.error.HTTPError as error:
        # Never print provider response bodies, request headers, or credentials.
        raise Stop(f'API request failed with HTTP {error.code}.') from None


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise Stop('Invalid repository name.')
        self.repository = repository
        self.token = token
        self.prefix = f'https://api.github.com/repos/{repository}/'

    def api(self, path, data=None, method=None):
        return request_json(self.prefix + path, self.token, data, method)

    def pages(self, path):
        items = []
        for page in range(1, 11):
            values = self.api(f'{path}{"&" if "?" in path else "?"}per_page=100&page={page}')
            items.extend(values)
            if len(values) < 100:
                return items
        raise Stop('Too many GitHub API results; no partial processing.')


def require_sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise Stop('Invalid commit identity.')
    return value


def require_number(value):
    value = str(value)
    if not value.isascii() or not value.isdigit() or int(value) < 1:
        raise Stop('A positive integer PR number is required.')
    return int(value)


def eligible(pr):
    if pr.get('user', {}).get('id') != AUTHOR_ID:
        raise Stop(f'Skipped: this rollout only handles PRs authored by {AUTHOR_LOGIN}.')
    if pr.get('state') != 'open' or pr.get('draft'):
        raise Stop('Skipped: the original PR must be open and ready for review.')
    if not pr.get('head', {}).get('repo'):
        raise Stop('Skipped: the source repository no longer exists.')
    if pr['head']['ref'].startswith('shizhen-fix/'):
        raise Stop('Skipped: never fix a generated fix branch.')
    require_sha(pr['head']['sha'])


def allowed_path(path):
    if (not isinstance(path, str) or not path.isascii() or '\\' in path
            or any(ord(char) < 32 for char in path)):
        return False
    parts = PurePosixPath(path).parts
    if not parts or path.startswith('/') or any(part in ('.', '..', '.git') for part in parts):
        return False
    if str(PurePosixPath(path)) != path:
        return False
    return ((path.startswith(('src/main/java/', 'src/test/java/')) and path.endswith('.java'))
            or path in ('docs/UserGuide.md', 'docs/DeveloperGuide.md'))


def file_at(gh, sha, path):
    # The Contents API can resolve symlinks as files. Check the immutable Git mode first.
    if not hasattr(gh, '_trees'):
        gh._trees = {}
    if sha not in gh._trees:
        commit = gh.api(f'git/commits/{require_sha(sha)}')
        tree = gh.api(f'git/trees/{require_sha(commit["tree"]["sha"])}?recursive=1')
        if tree.get('truncated'):
            raise Stop('Repository tree was truncated; refusing ambiguous file modes.')
        gh._trees[sha] = {entry['path']: entry for entry in tree['tree']}
    entry = gh._trees[sha].get(path, {})
    if entry.get('mode') != '100644' or entry.get('type') != 'blob':
        raise Stop('Only ordinary non-executable source/guide files may be edited.')
    item = gh.api(f'contents/{urllib.parse.quote(path, safe="/")}?ref={require_sha(sha)}')
    if not isinstance(item, dict) or item.get('type') != 'file' or item.get('size', 0) > MAX_FILE_BYTES:
        raise Stop('File is not a supported regular text file.')
    raw = base64.b64decode(item['content'], validate=False)
    if len(raw) > MAX_FILE_BYTES or b'\0' in raw:
        raise Stop('File is binary or exceeds the size limit.')
    return raw.decode('utf-8')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def apply_edits(edits, originals, permitted):
    if not isinstance(edits, list) or len(edits) > 24:
        raise Stop('Invalid edit list.')
    updated = dict(originals)
    changed = set()
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {'path', 'before', 'after'}:
            raise Stop('Edits must contain exactly path, before, and after.')
        path, before, after = edit['path'], edit['before'], edit['after']
        if not allowed_path(path) or path not in permitted or path not in updated:
            raise Stop('Edit targets an unsupported or unrelated file.')
        if not isinstance(before, str) or not isinstance(after, str) or not before or before == after:
            raise Stop('Empty, non-text, or ineffective edit.')
        if updated[path].count(before) != 1:
            raise Stop('Edit does not match exactly one location in the reviewed commit.')
        updated[path] = updated[path].replace(before, after, 1)
        if len(updated[path].encode()) > MAX_FILE_BYTES or '\0' in updated[path]:
            raise Stop('Updated file exceeds the text-file limits.')
        changed.add(path)
    if len(changed) > 8:
        raise Stop('Too many changed files for one bounded fix attempt.')
    return {path: updated[path] for path in sorted(changed) if updated[path] != originals[path]}


def load_json(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_PROPOSAL_BYTES:
        raise Stop('Artifact exceeds the size limit.')
    return json.loads(raw)


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n')


def output(name, value):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write(f'{name}={value}\n')


def summary(message):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
        stream.write(message + '\n')


def handoff_from_run(gh, run_id):
    run_id = require_number(run_id)
    run = gh.api(f'actions/runs/{run_id}')
    if (run.get('path') != '.github/workflows/shizhen-review.yml'
            or run.get('name') != 'shizhen-review' or run.get('conclusion') != 'success'
            or run.get('event') not in ('pull_request_target', 'workflow_dispatch')
            or run.get('repository', {}).get('full_name') != gh.repository):
        raise Stop('The source run is not a successful trusted shizhen-review run.')
    artifacts = gh.api(f'actions/runs/{run_id}/artifacts')['artifacts']
    attempt = run.get('run_attempt', 1)
    matches = [item for item in artifacts if item['name'] == f'shizhen-review-handoff-{attempt}'
               and not item.get('expired')]
    if not matches:
        raise Stop('Skipped: no eligible review handoff in this run.')
    if len(matches) != 1:
        raise Stop('Ambiguous review handoff artifact.')
    request = urllib.request.Request(
        gh.prefix + f'actions/artifacts/{matches[0]["id"]}/zip',
        headers={'Authorization': f'Bearer {gh.token}', 'User-Agent': 'shizhen-fix'})
    with open_request(request, timeout=45) as response:
        raw = response.read(MAX_PROPOSAL_BYTES + 1)
    if len(raw) > MAX_PROPOSAL_BYTES:
        raise Stop('Review artifact exceeds the size limit.')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) != 1 or entries[0].filename != 'handoff.json':
            raise Stop('Unexpected files in the review artifact.')
        if entries[0].file_size > MAX_PROPOSAL_BYTES:
            raise Stop('Review artifact expands beyond the size limit.')
        data = json.loads(archive.read(entries[0]))
    if (data.get('repository') != gh.repository or data.get('run_id') != run_id
            or data.get('run_attempt') != attempt):
        raise Stop('Review artifact provenance mismatch.')
    return data


def manual_handoff(gh, number):
    # Manual runs consume the same authenticated artifact, never arbitrary PR comments.
    runs = gh.api('actions/workflows/shizhen-review.yml/runs?status=success&per_page=30')
    for run in runs['workflow_runs']:
        try:
            data = handoff_from_run(gh, run['id'])
        except Stop:
            continue
        if data.get('pr_number') == number:
            return data
    raise Stop('No recent successful shizhen-review handoff exists for this PR.')


def generate(gh):
    output('proposed', 'false')
    event = load_json(os.environ['GITHUB_EVENT_PATH'])
    if os.environ['GITHUB_EVENT_NAME'] == 'workflow_run':
        data = handoff_from_run(gh, event['workflow_run']['id'])
    else:
        number = require_number(event['inputs']['pr_number'])
        # Enforce author restriction before looking up any review or spending tokens.
        eligible(gh.api(f'pulls/{number}'))
        data = manual_handoff(gh, number)
    number = require_number(data['pr_number'])
    pr = gh.api(f'pulls/{number}')
    eligible(pr)
    sha = require_sha(data['head_sha'])
    if pr['head']['sha'] != sha:
        raise Stop('Skipped: the reviewed commit is no longer the PR head.')
    commits = gh.pages(f'pulls/{number}/commits')
    if any(item['commit']['message'].startswith('Apply shizhen-fix') for item in commits):
        raise Stop('Skipped: this PR already contains an accepted automatic fix.')
    findings = data.get('review', {}).get('review', {}).get('key_issues_to_review', [])
    if not isinstance(findings, list) or not findings:
        raise Stop('No actionable review findings; no fix PR needed.')
    if len(findings) > 20:
        raise Stop('Too many findings for a single bounded fix attempt.')
    changed = gh.pages(f'pulls/{number}/files')
    permitted = {item['filename'] for item in changed
                 if item['status'] in ('added', 'modified', 'renamed') and allowed_path(item['filename'])}
    files = {path: file_at(gh, sha, path) for path in sorted(permitted)}
    if not files:
        raise Stop('No supported Java or guide files in this PR; no automatic edits.')
    if (len(files) > SETTINGS['max_files']
            or sum(len(text.encode()) for text in files.values()) > SETTINGS['max_source_chars']):
        raise Stop('PR exceeds the bounded context limit; human fixes required.')
    token = os.environ.get('LLM_API_KEY', '')
    if not token:
        raise Stop('Missing SoCLaaS repository secret LLM_API_KEY.')
    # An atomic ref reservation makes repeated runs, no-fix results and failures idempotent.
    branch = f'shizhen-fix/pr-{number}-{sha[:12]}'
    try:
        gh.api('git/refs', {'ref': 'refs/heads/' + branch, 'sha': sha})
    except Stop as error:
        if 'HTTP 422' in str(error):
            # A 422 can also mean an invalid commit. Verify the branch actually exists.
            existing = gh.api('git/ref/heads/' + urllib.parse.quote(branch, safe='/'))
            if existing.get('object', {}).get('sha'):
                raise Stop('Skipped: this PR commit already has a reserved fix attempt.') from None
        raise
    instructions = (ROOT / 'instructions.md').read_text()
    standards = ROOT.parent / 'shizhen-review' / 'course-standards.md'
    instructions += '\n\n' + standards.read_text()
    context = json.dumps({'findings': findings, 'files': files,
                          'changed_files': [item['filename'] for item in changed]}, ensure_ascii=False)
    if len((instructions + context).encode()) > 65_000:
        raise Stop('Combined review context exceeds the initial rollout budget.')
    response = request_json(ENDPOINT, token, {
        'model': MODEL, 'reasoning_effort': 'high', 'max_completion_tokens': 8192,
        'messages': [{'role': 'system', 'content': instructions},
                     {'role': 'user', 'content': context}],
    })
    choice = response['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise Stop('Model output was incomplete; no changes published.')
    text = choice['message']['content'].strip()
    if text.startswith('```json\n') and text.endswith('\n```'):
        text = text[8:-4]
    plan = json.loads(text)
    if not isinstance(plan, dict) or set(plan) != {'decisions', 'edits'}:
        raise Stop('Invalid model response schema.')
    decisions = plan['decisions']
    if (not isinstance(decisions, list) or len(decisions) != len(findings)
            or {item.get('finding') for item in decisions} != set(range(1, len(findings) + 1))
            or any(item.get('decision') not in ('fix', 'skip')
                   or not isinstance(item.get('reason'), str) or not item['reason'].strip()
                   or len(item['reason']) > 2000 for item in decisions)):
        raise Stop('Each finding needs exactly one justified fix/skip decision.')
    updated = apply_edits(plan['edits'], files, permitted)
    if not updated:
        summary('No substantiated, supported fixes were proposed. The original PR is unchanged.\n\n'
                + '\n'.join(f'* Finding {item["finding"]}: {item["reason"]}' for item in decisions))
        return
    if not any(item['decision'] == 'fix' for item in decisions):
        raise Stop('Edits were returned without an accepted finding.')
    save('proposal.json', {
        'repository': gh.repository, 'pr_number': number, 'head_sha': sha,
        'branch': branch, 'decisions': decisions, 'edits': plan['edits'],
        'original_hashes': {path: digest(files[path]) for path in updated},
        'review_run_id': data['run_id'],
    })
    output('proposed', 'true')
    summary(f'Prepared a bounded fix proposal for PR #{number} at `{sha}`. Tests and human review remain.')


def validate_proposal(gh, proposal):
    if proposal.get('repository') != gh.repository:
        raise Stop('Proposal repository mismatch.')
    number = require_number(proposal['pr_number'])
    pr = gh.api(f'pulls/{number}')
    eligible(pr)
    sha = require_sha(proposal['head_sha'])
    if pr['head']['sha'] != sha:
        raise Stop('The original PR changed; no stale fix will be published.')
    if proposal['branch'] != f'shizhen-fix/pr-{number}-{sha[:12]}':
        raise Stop('Invalid proposal branch.')
    permitted = {item['filename'] for item in gh.pages(f'pulls/{number}/files')
                 if item['status'] in ('added', 'modified', 'renamed') and allowed_path(item['filename'])}
    paths = {edit['path'] for edit in proposal['edits']}
    if not paths.issubset(permitted):
        raise Stop('Proposal edits a file outside the original PR scope.')
    originals = {path: file_at(gh, sha, path) for path in paths}
    updated = apply_edits(proposal['edits'], originals, permitted)
    if not updated or proposal['original_hashes'] != {path: digest(originals[path]) for path in updated}:
        raise Stop('Proposal content does not match the reviewed immutable files.')
    return pr, updated


def materialize(gh):
    proposal = load_json('proposal.json')
    _, updated = validate_proposal(gh, proposal)
    sha = proposal['head_sha']
    request = urllib.request.Request(gh.prefix + f'tarball/{sha}', headers={
        'Authorization': f'Bearer {gh.token}', 'User-Agent': 'shizhen-fix'})
    with open_request(request, timeout=60) as response:
        raw = response.read(30_000_001)
    if len(raw) > 30_000_000:
        raise Stop('Source archive exceeds the size limit.')
    target = Path('candidate')
    target.mkdir()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers()
        if len(members) > 10000 or sum(item.size for item in members) > 100_000_000:
            raise Stop('Source archive expands beyond limits.')
        for member in members:
            parts = PurePosixPath(member.name).parts
            if (not parts or member.name.startswith('/') or '..' in parts or '.git' in parts
                    or not (member.isfile() or member.isdir())):
                raise Stop('Unsafe archive entry; symlinks and special files are not supported.')
            if len(parts) == 1:
                continue
            path = target.joinpath(*parts[1:])
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.extractfile(member).read())
    for path, content in updated.items():
        destination = target / path
        if not destination.is_file():
            raise Stop('Proposed file missing from the source archive.')
        if digest(destination.read_text()) != proposal['original_hashes'][path]:
            raise Stop('Archive content differs from the reviewed immutable source.')
        destination.write_text(content)
    # Only this disposable copy is writable by the unprivileged test container.
    for path in [target, *target.rglob('*')]:
        path.chmod(0o777 if path.is_dir() else 0o666)


def publish(gh):
    proposal = load_json('proposal.json')
    pr, updated = validate_proposal(gh, proposal)
    number, sha, branch = proposal['pr_number'], proposal['head_sha'], proposal['branch']
    ref = gh.api('git/ref/heads/' + urllib.parse.quote(branch, safe='/'))
    if ref['object']['sha'] != sha:
        raise Stop('Fix branch already changed; refusing to overwrite it.')
    original_commit = gh.api(f'git/commits/{sha}')
    entries = []
    for path, content in updated.items():
        blob = gh.api('git/blobs', {'content': content, 'encoding': 'utf-8'})
        entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    tree = gh.api('git/trees', {'base_tree': original_commit['tree']['sha'], 'tree': entries})
    commit = gh.api('git/commits', {'message': f'Apply shizhen-fix for PR #{number}',
                                    'tree': tree['sha'], 'parents': [sha]})
    # Revalidate just before mutating our branch or opening the PR.
    validate_proposal(gh, proposal)
    gh.api('git/refs/heads/' + urllib.parse.quote(branch, safe='/'),
           {'sha': commit['sha'], 'force': False}, 'PATCH')
    fork = pr['head']['repo']['full_name'] != gh.repository
    base = pr['base']['ref'] if fork else pr['head']['ref']
    status = os.environ.get('VALIDATION_RESULT', 'unknown')
    run_url = f'https://github.com/{gh.repository}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
    mode = (f'Replacement for #{number}: includes its original changes plus the proposed fixes. '
            'The original fork branch is unchanged. Choose this PR or keep the original; do not merge both.'
            if fork else f'Fixes for #{number}: merge this draft into the original PR branch only after human review.')
    decisions = '\n'.join(f'* Finding {item["finding"]}: **{item["decision"]}** — '
                          + item['reason'].replace('@', '@\u200b')
                          for item in proposal['decisions'])
    body = (f'<!-- shizhen-fix:original:{number}:{sha} -->\n\n{mode}\n\n'
            f'Reviewed original commit: `{sha}`. Model: SoCLaaS `{MODEL}`.\n\n'
            f'## Findings evaluated\n\n{decisions}\n\n'
            f'## Verification\n\nIsolated Gradle check/coverage job: **{status}**. '
            f'[Run and test logs]({run_url}). Failures or missing checks leave this draft for investigation. '
            'A successful test job is not a guarantee of correctness.\n\n'
            'No automatic approval or merge is performed. The source PR remains open and unchanged. '
            'This generated branch is excluded from automatic fix attempts.\n')
    created = gh.api('pulls', {'title': f'shizhen-fix: Propose fixes for PR #{number}',
                              'head': branch, 'base': base, 'draft': True, 'body': body})
    summary(f'Draft fix PR: {created["html_url"]}\n\nOriginal PR: {pr["html_url"]} (unchanged).')


def handoff(gh):
    number = require_number(os.environ['PR_NUMBER'])
    pr = gh.api(f'pulls/{number}')
    try:
        eligible(pr)
    except Stop as error:
        summary(str(error) + ' The review still runs; no fix handoff is created.')
        return
    save('review-head.json', {'repository': gh.repository, 'pr_number': number,
                              'head_sha': pr['head']['sha'],
                              'run_id': int(os.environ['GITHUB_RUN_ID']),
                              'run_attempt': int(os.environ.get('GITHUB_RUN_ATTEMPT', '1'))})


def finish_handoff(gh):
    data = load_json('review-head.json')
    pr = gh.api(f'pulls/{require_number(data["pr_number"])}')
    eligible(pr)
    if pr['head']['sha'] != data['head_sha']:
        raise Stop('PR changed during review; no fix handoff published.')
    data['review'] = load_json('review-data.json')
    Path('review-handoff').mkdir(exist_ok=True)
    save('review-handoff/handoff.json', data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['generate', 'materialize', 'publish', 'handoff', 'finish-handoff'])
    command = parser.parse_args().command
    gh = GitHub(os.environ['GITHUB_REPOSITORY'], os.environ['GH_TOKEN'])
    try:
        {'generate': generate, 'materialize': materialize, 'publish': publish,
         'handoff': handoff, 'finish-handoff': finish_handoff}[command](gh)
    except Stop as error:
        summary(str(error))
        # Ordinary rollout/idempotency/no-findings skips are successful no-ops.
        if command == 'generate' and str(error).startswith(('Skipped:', 'No actionable', 'No supported')):
            return
        raise SystemExit(str(error)) from None


if __name__ == '__main__':
    main()

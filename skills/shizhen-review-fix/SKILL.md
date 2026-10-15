---
name: shizhen-review-fix
description: Install, configure, or audit the shizhen-review and shizhen-fix GitHub Actions pair for author-restricted, human-reviewed AI repair PRs using an OpenAI-compatible gateway. Use for this workflow's setup and maintenance, not ordinary code review.
---

# shizhen-review-fix

The implementation is published at [shiverin/shizhen-review-fix](https://github.com/shiverin/shizhen-review-fix). Clone that repository to obtain its deterministic `install.py`, `templates/`, and test suite. Read its [setup guide](https://github.com/shiverin/shizhen-review-fix/blob/main/README.md) for installation or [architecture](https://github.com/shiverin/shizhen-review-fix/blob/main/docs/architecture.md) when changing triggers, permissions, or artifacts. This skill folder can be installed independently; it does not contain the implementation.

Confirm the target repository and the one allowed PR author. Resolve the author's numeric GitHub ID, then run the installer against the intended checkout. It refuses to overwrite existing workflow files. Keep the existing reviewer intact unless the user explicitly requests replacing it.

The distributed profile is Java/Gradle with CS2103T conventions and SoCLaaS `x-test-1`. For another project, adapt both review/fix instructions, the permitted-path function, and the isolated test command together. A different model or endpoint needs a tested provider adapter; changing a label is insufficient.

Preserve the following invariants when configuring or maintaining the workflow:

* The fixer checks the configured numeric author ID in handoff, generation, materialization, and publication; manual runs cannot bypass it.
* Only successful trusted reviewer runs may supply findings. Bind artifacts to their run, repository, PR number, and immutable head commit. Reject stale heads.
* Privileged jobs never execute PR/model-generated code. Tests run in a disposable container without repository credentials, API keys, host tools, or shared caches. The publisher consumes the original proposal, not test-modified files.
* Reserve one automatic attempt per original commit, exclude fix branches, and stop once accepted automatic fix commits appear in the original PR. Never create unbounded repair loops.
* Keep fix PRs draft. Never approve, merge, close the original PR, change its source branch, or treat passing tests as proof of correctness.

After changes, run `python3 -m unittest discover -s tests -v` and actionlint on the template workflows. Verify author denial, stale-head rejection, path/mode validation, and draft-only publication. The test suite uses fake API calls and does not prove live model or runner compatibility. Report any unverified live steps explicitly. Do not request keys in chat, commit credentials, overwrite repository secrets, or enable repository-wide Actions permissions without the user's authorization.

# shizhen-review

An independent review workflow using SoCLaaS `x-test-1` with high reasoning effort and the existing encrypted `LLM_API_KEY` repository secret. It does not change `ai-review.yml`. The workflow runs when a PR is opened, updated, reopened, or marked ready for review; it can also be run manually with a PR number after it reaches the default branch.

Reviews use the pinned PR-Agent engine, with inline findings and a persistent overall comment headed **shizhen-review**. GitHub posts them as `github-actions[bot]`: renaming the workflow does not rename that account. A separate GitHub App would be needed for a custom account identity. Reviews are advisory and do not approve or merge PRs.

The primary format is CS2103T's referenced SE-EDU guidance: specific code locations, constructive questions, explanations, and non-repetitive feedback. Google Engineering Practices supplements it. Sources are linked in [instructions.md](instructions.md); [course-standards.md](course-standards.md) contains the offline course convention rules used by the reviewer. Review findings have severity labels, evidence, impact, and a proposed correction or regression test.

Only trusted workflow-branch instructions are checked out. PR code is read as diff data through GitHub's API and is never executed by this workflow. PR-provided settings and global settings are disabled. Credentials are exposed only to the review step. No model fallback is configured. A small compatibility adapter namespaces the pinned engine's review comment markers and legacy headings, preventing either reviewer from replacing the other's overall comment; it fails if the expected engine definitions change.

The reviewer analyzes changed hunks with surrounding lines, not the entire repository, and does not execute tests. Large diffs are split into at most eight model calls; at most twenty findings are returned. The review coverage footer identifies omitted content, so a capped review must not be treated as complete. Each model call has a 280-second timeout and no automatic retry; the job has a 45-minute limit. Provider errors fail the workflow instead of being presented as a clean review.

## Setup and verification

Create the encrypted repository secret `LLM_API_KEY` for your SoCLaaS credential. This workflow fixes the endpoint to `https://soclaas-api.comp.nus.edu.sg/v1` and the model to `x-test-1`; it does not read model or endpoint variables. Never commit a key to the repository.

Local checks validate workflow syntax, instruction loading, and the selected engine's configuration fields. End-to-end provider authentication, model availability, and publication must be verified in your own repository with a small live pilot.

After merging, run a one-off review without opening a new PR:

```bash
gh workflow run shizhen-review.yml --repo OWNER/REPO -f pr_number=PR_NUMBER
```

The workflow is supplementary feedback; teammates still perform their own course-required peer reviews.

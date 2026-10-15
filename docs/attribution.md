# Attribution

Shizhen proposed the workflow shape in conversation: automatically review a PR, validate the review rather than blindly follow it, produce a separate optional repair PR, and let a human accept the repair or return to the original. The initial rollout was then narrowed to the author's own PRs. This package records those decisions without claiming novelty or universal reliability.

Codex assisted with implementation, tests, packaging, and documentation.

The review engine is installed from `qodo-ai/pr-agent` at commit `330f0813b5fe0d1f54b794077c2d02aa85a1fb63`; it is not vendored into this package. Consult its upstream license and dependency licenses. `namespace-engine.py` adapts that pinned installation's comment identity definitions so its review comments remain distinct from another deployment of the same engine.

Review tone and structure follow SE-EDU's publicly documented PR practices, with supplementary Google Engineering Practices guidance. The offline course convention reference summarizes CS2103T/SE-EDU requirements from a local standards skill assembled on 2026-08-17. It is dated reference material, not a replacement for current course instructions. Source links are included with the template. Institution and product names identify interoperability and reference sources; no endorsement is implied.

No credentials, private course artifacts, original pull-request source files, user memory files, chat transcripts, or raw screenshots are included. The default public example names the author's public GitHub account and numeric ID; the installer configures a different intended author when reused.

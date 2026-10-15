"""Namespace the pinned engine's comment markers for this independent reviewer."""

import importlib.util
from pathlib import Path


def namespace_source(source):
    """Adapt only the exact marker definitions in the pinned upstream engine."""
    replacements = {
        'REGULAR = "## PR Reviewer Guide"': 'REGULAR = "## shizhen-review"',
        'INCREMENTAL = "## Incremental PR Reviewer Guide"':
            'INCREMENTAL = "## Incremental shizhen-review"',
        'REGULAR = "<!-- pr-agent:review:full -->"':
            'REGULAR = "<!-- shizhen-review:review:full -->"',
        'INCREMENTAL = "<!-- pr-agent:review:incremental -->"':
            'INCREMENTAL = "<!-- shizhen-review:review:incremental -->"',
    }
    for original, replacement in replacements.items():
        if source.count(original) != 1:
            raise RuntimeError('Pinned review-engine marker definitions changed.')
        source = source.replace(original, replacement, 1)
    return source


if __name__ == '__main__':
    package = importlib.util.find_spec('pr_agent')
    if package is None or package.origin is None:
        raise RuntimeError('The pinned review engine must be installed first.')
    identity = Path(package.origin).parent / 'algo' / 'comment_identity.py'
    identity.write_text(namespace_source(identity.read_text()))

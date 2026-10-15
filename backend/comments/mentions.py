"""FR-045: parse @username mentions out of a comment body."""
import re

from tasks.access import task_participants

MENTION_RE = re.compile(r'(?<!\w)@([A-Za-z0-9_.]{1,150})')


def extract_mentions(body, task):
    """
    Every user named with @username in `body` who can actually see `task` - in the order
    they first appear, case-insensitive, de-duplicated. Names that don't match anyone
    with visibility are silently ignored rather than erroring, so a stray "@" in prose
    doesn't block posting a comment.
    """
    seen = []
    for name in MENTION_RE.findall(body):
        low = name.lower()
        if low not in seen:
            seen.append(low)
    if not seen:
        return []
    by_username = {u.username.lower(): u for u in task_participants(task)}
    return [by_username[name] for name in seen if name in by_username]

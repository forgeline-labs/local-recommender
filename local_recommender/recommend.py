"""Core recommendation algorithm.

Items are related with binary cosine similarity over the sets of users that
interacted with them. The implementation is a pure function: it never mutates
its arguments, performs no I/O and keeps no global caches.
"""

import math
import re

MAX_INTERACTIONS = 10000
MAX_USERS = 1000
MAX_ITEMS = 1000
MIN_LIMIT = 1
MAX_LIMIT = 100
SCORE_DECIMALS = 6

_IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,32}")
_RECORD_KEYS = frozenset({"user", "item"})


def _validate_identifier(value, field):
    """Return ``value`` if it is a valid identification string."""
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{field} must be a string matching [A-Za-z0-9_-]{{1,32}}")
    return value


def _validate_interactions(interactions):
    """Validate the interaction list and return its deduplicated pairs."""
    if not isinstance(interactions, list):
        raise ValueError("interactions must be a list")
    if len(interactions) > MAX_INTERACTIONS:
        raise ValueError(f"interactions must contain at most {MAX_INTERACTIONS} records")

    pairs = set()
    for index, record in enumerate(interactions):
        if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
            raise ValueError(
                f"interaction at index {index} must be an object with exactly 'user' and 'item'"
            )
        user = _validate_identifier(record["user"], "user")
        item = _validate_identifier(record["item"], "item")
        pairs.add((user, item))
    return pairs


def _validate_limit(limit):
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer between 1 and 100")
    if not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise ValueError("limit must be an integer between 1 and 100")
    return limit


def _published_score(score):
    """Round the final score to six decimals, half-even, without negative zero."""
    rounded = round(score, SCORE_DECIMALS)
    if rounded == 0.0:
        return 0.0
    return rounded


def recommend(interactions, user, limit=5):
    """Recommend items for ``user`` from binary ``interactions``.

    Parameters
    ----------
    interactions:
        A list of at most 10000 exact ``{"user": ..., "item": ...}`` objects.
    user:
        The user to recommend for; an ASCII identification string.
    limit:
        A strict integer in ``1..100``.

    Returns
    -------
    list[dict]
        At most ``limit`` ``{"item": ..., "score": ...}`` objects sorted by
        descending score rounded to six decimal places, then by ascending
        ASCII item. Unknown users and users without positive candidates
        yield an empty list.
    """
    pairs = _validate_interactions(interactions)
    _validate_identifier(user, "user")
    _validate_limit(limit)

    users = {record_user for record_user, _ in pairs}
    items = {item for _, item in pairs}
    if len(users) > MAX_USERS:
        raise ValueError(f"at most {MAX_USERS} distinct users are supported")
    if len(items) > MAX_ITEMS:
        raise ValueError(f"at most {MAX_ITEMS} distinct items are supported")

    users_of = {}
    for record_user, item in pairs:
        users_of.setdefault(item, set()).add(record_user)

    seen = {item for record_user, item in pairs if record_user == user}
    candidates = users_of.keys() - seen

    # Sim(i, j) = |U(i) & U(j)| / sqrt(|U(i)| * |U(j)|). Terms are summed
    # without intermediate rounding; fsum keeps the 64-bit result stable
    # against the iteration order of hash-based sets.
    seen_terms = sorted((item, users_of[item], len(users_of[item])) for item in seen)
    scored = []
    for item in candidates:
        item_users = users_of[item]
        item_user_count = len(item_users)
        score = math.fsum(
            len(seen_users & item_users) / math.sqrt(seen_count * item_user_count)
            for _seen_item, seen_users, seen_count in seen_terms
        )
        if score == 0.0:
            continue
        scored.append((item, _published_score(score)))

    scored.sort(key=lambda entry: (-entry[1], entry[0]))
    return [{"item": item, "score": score} for item, score in scored[:limit]]

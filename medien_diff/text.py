import string

_NOISE_CHARS = frozenset(string.punctuation) | frozenset(string.digits)


def is_significant_title_change(old, new):
    if _is_bad_title(old) or _is_bad_title(new):
        return False

    old_key = _title_equality_key(old)
    new_key = _title_equality_key(new)

    if abs(len(old_key) - len(new_key)) > 1:
        return True

    neq_count = sum(int(a != b) for a, b in zip(old_key, new_key))

    if neq_count > 2:
        return True

    return False


def _is_bad_title(title):
    """
    Filter out tweets about live sports events from Kronenzeitung
    """

    return title.strip().lower().startswith("live:")


def _title_equality_key(title):
    title = "".join(
        c for c in " ".join(title.upper().strip().split()) if c not in _NOISE_CHARS
    )
    return " ".join(sorted(title.split()))

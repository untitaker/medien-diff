import string

_NOISE_CHARS = frozenset(string.punctuation) | frozenset(" ")


def is_significant_title_change(old, new):
    if _is_bad_title(old) or _is_bad_title(new):
        return False

    return _title_equality_key(old) != _title_equality_key(new)


def _is_bad_title(title):
    """
    Filter out tweets about live sports events from Kronenzeitung
    """

    return title.strip().lower().startswith("live:")


def _title_equality_key(title):
    return [c for c in "".join(title.strip().split()) if c not in _NOISE_CHARS]

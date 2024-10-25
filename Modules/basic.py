"""
Common functions for most cogs and modules.
Discord.py is not allowed here; see 'discord_utils' MOD for those.
Below imports should not include any built-in's, to avoid cyclic imports.
"""



##################################################
# IMPORTS
##################################################



from __main__ import __file__
from os import path as os_path



##################################################
# GLOBALS
##################################################



# Default spacing for the mixmatch function
_SPACING = ["", "-", "_"]
# Punctuation for the remove_punct function
_PUNCT = ['.', ',', '?', '!', ';', ':', '"', "'", " "]


##################################################
# FUNCTIONS
##################################################



def isiterable(var: any, allowstring: bool = False):
    """Check if a variable is iterable or not (targeted at for-loops)"""
    if allowstring and isinstance(var, str): return True
    return isinstance(var, (list, tuple, set, dict, frozenset, range,))


def makeiterable(var: any, default_to: str = "list") -> any:
    """Make a variable iterable, if it isn't already"""
    if isiterable(var): return var
    allowed = {"list": list, "tuple": tuple, "set": set}
    # Neither a key nor a value in allowed
    if default_to not in allowed.keys() and default_to not in allowed.values():
        raise TypeError(f"Type '{default_to}' is not allowed")
    # Resolve the type using the dictionnary
    if isinstance(default_to, str): default_to = allowed[default_to]
    return default_to([var]) if var is not None else default_to()


def mixmatch(part1: list, part2: list, spacing: list = _SPACING,
             keeporder: bool = False, remove: str = None) -> list:
    """
    Create an exhaustive list of names matched from one element of each list.
    Since returned value is a list, do not hesitate to use mixmatch() + mixmatch().
    """
    if not remove: remove = set()
    names = []
    # Ensure all iterable arguments are converted if needed
    part1 = makeiterable(part1); part2 = makeiterable(part2)
    spacing = makeiterable(spacing); remove = makeiterable(remove, "set")
    # Three-fold iteration
    for p1 in part1:
        for p2 in part2:
            for s in spacing:
                if not p1 or not p2: s= "" # If either is empty, disable spacing ----------+
                names.append(f"{p1}{s}{p2}")                                             # |
                if not p1 or not p2: break # And only apply the loop once   <--------------+
                # Append name in 'wrong order' if implementation hasn't disallowed it
                if not keeporder: names.append(f"{p2}{s}{p1}")
    return [n for n in names if n and n not in remove]


def remove_punct(txt: str) -> str:
    """Remove punctuation from a string"""
    for p in _PUNCT:
        txt = txt.replace(p, "")
    return txt


def plural(obj: any, _n = "s", _0 = "s", _1 = "", _p = "s") -> any:
    """Return a value based on the len of obj."""
    n = n if isinstance(obj, int) else len(obj)
    match n:
        case 0: return _0
        case 1: return _1
        case _: return _n if n<0 else _p
    


def least_one(iter1, iter2) -> bool:
    """Check if there is at least one element that is both in iter1 and iter2."""
    return any(i in iter1 for i in iter2)


def project_root() -> str:
    """Return absolute path to the project root directory."""
    return os_path.dirname(os_path.realpath(__file__))


def correspond(needle: str, haystack: set()) -> str:
    """
    Return the first element in haystack that matches needle.
    First by exact match, then prefix, then inclusion.
    """
    haystack = makeiterable(haystack, "set")
    if needle in haystack:
        return needle
    for h in haystack:
        if h.startswith(needle):
            return h
    # Inclusion match
    for h in haystack:
        if needle in h:
            return h
    # Nothing
    return None


##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass
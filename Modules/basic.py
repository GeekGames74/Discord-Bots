"""
Common functions for most cogs and modules.
Discord.py is not allowed here; see 'discord_utils' MOD for those.
"""



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



def least_one(iter1, iter2) -> bool:
    """Check if there is at least one element that is both in iter1 and iter2."""
    return any(i in iter1 for i in iter2)


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


def flatten(iter: list, new_iter: list = None) -> list:
    """Flatten a list of lists (of lists...)"""
    if new_iter is None:
        new_iter = set() if isinstance(iter, set) else []
    if isiterable(iter): # If it's an iterable
        for i in iter: flatten(i, new_iter) # Apply recursively
    elif isinstance(new_iter, set): # The method to add to new_iter changes :
        new_iter.add(iter) # If it's a set, it's set.add()
    else: new_iter.append(iter) # On lists, it's list.append()
    return new_iter


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
                if not p1 or not p2: s= "" # If either is empty, disable spacing -----+
                names.append(f"{p1}{s}{p2}") # Add as normal                        # |
                if not p1 or not p2: break # And only apply the loop once   <---------+
                # Append name in 'wrong order' if implementation hasn't disallowed it
                if not keeporder: names.append(f"{p2}{s}{p1}")
    return [n for n in names if n and n not in remove]


def removepunct(txt: str) -> str:
    """Remove punctuation from a string"""
    for p in _PUNCT: txt = txt.replace(p, "")
    return txt


def plural(obj: any, _n = "s", _0 = "s", _1 = "", _p = "s") -> any:
    """Return a value based on the len of obj."""
    n = obj if isinstance(obj, int) else len(obj)
    match n:
        case 0: return _0
        case 1: return _1
        case _: return _n if n < 0 else _p


def correspond(needle: str, haystack: set()) -> str:
    """
    Return the first element in haystack that matches needle.
    First by exact match, then prefix, then inclusion.
    """
    haystack = makeiterable(haystack, "set")
    if needle in haystack: return needle # Exact match
    for h in haystack: # Prefix match
        if h.startswith(needle): return h
    for h in haystack: # Inclusion match
        if needle in h: return h
    return None # Nothing


def surround(txt, prefix) -> str:
    """
    Return string enclosed by (), optionally with prefix.
    If txt is iterable, sep them with ','
    """
    if isiterable(txt): txt = ','.join(txt)
    return f"{prefix}({txt})" if prefix else f"({txt})"


def yes_no(txt: str) -> bool:
    """Evaluate text to answer true or false"""
    txt = txt.lower()
    if correspond(txt, ["on", "yes", "true", "oui", "vrai"]): return True
    if correspond(txt, ["off", "non", "false", "faux"]): return False
    return None


def format_number(n: int|float|str, plural: bool = False) -> str:
    """Format a number with 10^3 unit name (thousand, million, billion, trillion)."""
    if isinstance(n, str): # Convert to number
        try: n = float(n) if "." in n else int(n)
        except ValueError: return n
    unit = 0
    while abs(n) >= 1000:
        n /= 1000
        unit += 1
    word = {0: "", 1: " thousand", 2: " million", 3: " billion", 4: " trillion"}
    plural = "" if plural and (unit == 0 or abs(n) == 1) else "s"
    return f"{round(n)}{word[unit]}{plural}"



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass
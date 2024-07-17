"""
Common functions for most cogs and modules.
No discord.py here !
"""


##########################################################################
# IMPORTS
##########################################################################


import os


##########################################################################
# CONSTANTS
##########################################################################


# Default spacing for the mixmatch function
_SPACING = ["", "-", "_"]


##########################################################################
# METHODS
##########################################################################


def isiterable(var: any, allowstring: bool = False):
    """Check if a variable is iterable or not (targeted at for-loops)"""
    if allowstring and isinstance(var, str): return True
    return isinstance(var, (list, tuple, set, dict, frozenset, range,))


def mixmatch(part1: list, part2: list, spacing: list = _SPACING, keeporder: bool = False) -> list:
    """
    Create an exhaustive list of names matched from one element of each list.
    Since returned value is a list, do not hesitate to use mixmatch() + mixmatch().
    """
    names = []
    # Ensure all iterable arguments are converted if needed
    if not isiterable(part1): part1 = [part1]
    if not isiterable(spacing): spacing = [spacing]
    if not isiterable(part2): part2 = [part2]
    # Three-fold iteration
    for p1 in part1:
        for p2 in part2:
            for s in spacing:
                if not p1 or not p2: s= "" # If either is empty, disable spacing ----------+
                names.append(f"{p1}{s}{p2}") #                                             |
                # Append name in 'wrong order' if implementation hasn't disallowed it      |
                if not keeporder: names.append(f"{p2}{s}{p1}") #                           |
                if not p1 or not p2: break # And only apply the loop once   <--------------+
    return names


def least_one(text, checkfor) -> bool:
    """Check if there is at least one of (checkfor) in (text)."""
    return any(i in text for i in checkfor)


def localpath(file: str = __file__) -> str:
    """Return absolute path to the current directory."""
    return os.path.dirname(os.path.realpath(file))



if __name__ == "__main__":
    pass
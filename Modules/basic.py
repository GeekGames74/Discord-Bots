"""
Common commands for most modules and modules.
No discord.py here !
"""



##########################################################################
# IMPORTS
##########################################################################



import os


##########################################################################
# CONSTANTS
##########################################################################


SPACING = ["", "-", "_"]


##########################################################################
# METHODS
##########################################################################


def mixmatch(part1: any, part2: any, spacing: any = SPACING, keeporder: bool = False) -> list:
    """Create an exhaustive name matched from one element of each list."""
    names = []
    if not isinstance(part1, (list, tuple)): part1 = [part1]
    if not isinstance(spacing, (list, tuple)): spacing = [spacing]
    if not isinstance(part2, (list, tuple)): part2 = [part2]
    for p1 in part1:
        for p2 in part2:
            for s in spacing:
                names.append(f"{p1}{s}{p2}")
                if not keeporder: names.append(f"{p2}{s}{p1}")
    return names


def least_one(text, checkfor) -> bool:
    """Check if there is at least one of (checkfor) in (text)."""
    return any(i in text for i in checkfor)


def local_path(file: str = __file__) -> str:
    """Return absolute path to the current file."""
    return os.path.dirname(os.path.realpath(file))



if __name__ == "__main__":
    pass
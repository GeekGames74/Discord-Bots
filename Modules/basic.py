"""
Common commands for most modules and modules.
No discord.py here !
"""



##########################################################################
# IMPORTS
##########################################################################



import os



##########################################################################
# BASIC
##########################################################################



def least_one(text, checkfor) -> bool:
    """Check if there is at least one of (checkfor) in (text)."""
    return any(i in text for i in checkfor)


def local_path(file: str = __file__) -> str:
    """Return absolute path to the current file."""
    return os.path.dirname(os.path.realpath(file))
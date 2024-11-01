"""
Module to securely retreive and write data.
Local formats (txt, json, local bd) or external (bd, endpoints...).
"""



##################################################
# IMPORTS
##################################################



from os import path as os_path
from json import load as json_load

from Modules.basic import path_from_root, makeiterable



##################################################
# FUNCTIONS
##################################################



def checkfile(name: str) -> str:
    """Tries to find a file in the current directory."""
    path = path_from_root(name)
    if os_path.isfile(path): return path
    raise FileNotFoundError(f"{path} was not found in current directory")


def with_data(source: str, *data: any):
    """Generic decorator to securely fetch data from a given source."""
    def decorator(func: callable) -> callable:
        def wrapper(*args, **kwargs) -> any:
            if source.endswith(".txt"):
                local_data = data_TXT(source, *data)
            elif source.endswith(".json"):
                local_data = data_JSON(source, *data)
            else: raise NotImplementedError(f"Cannot get data from {source}")
            kwargs.update(local_data)
            result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


# Data from .txt
def data_TXT(file: str, data: tuple = None) -> dict:
    """
    <data> is used to map indexes to variables.
    {VarNameToInject: IndexOfLine} as a Dict.
    [NameOfIndex0, NameOfIndex1,] as a List
    (will only get the indexes listed).
    If data is None, return every line in a tuple.
    """
    file = checkfile(file)
    local_data = {}
    with open(file, encoding="utf-8") as F:
        lines = F.readlines()
    # No mapping
    if data is None: return (l.removesuffix("\n") for l in lines)
    # Turn the list into a Dict of Value:Index
    data = makeiterable(data)
    data[0] = makeiterable(data[0])
    if isinstance(data[0], list):
        data[0] = {k:i for i,k in enumerate(data[0])}
    # Remember : readline() might return "\n" at the end of the line
    for i,j in data[0].items():
        local_data[i] = lines[j].removesuffix("\n")
    return local_data


# Data from .json
def data_JSON(file: str, data: tuple = None) -> dict:
    """
    <data[0]> can be used to remake the mapping of keys.
    {JsonKey: VarNameToInject} as a Dict.
    <data[1]> is bool to filter *out* keys with no express mapping
    (default False --> no filter)
    """
    file = checkfile(file)
    with open(file, encoding="utf-8") as F:
        content = json_load(F)
    # No special mapping; Proceed
    if data is None: return content
    # Remake the mapping of keys
    for k,v in content.items():
        if k in data[0]:
            content[data[0][k]] = v
        # Allow stranger key if not specified otherwise
        elif len(data) == 1 or not data[1]:
            content[k] = v
    return content



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass
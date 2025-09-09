"""
Module to securely retreive and write data.
Local formats (txt, json, local bd) or external (bd, endpoints...).
"""



##################################################
# IMPORTS
##################################################



from os import path as os_path
from os import sep as os_sep
from os import makedirs
from json import load, dump



##################################################
# CONSTANTS
##################################################



_ROOT = os_path.abspath(os_path.join(os_path.dirname(__file__), '..'))

_DATA_FORMATS = {
    "txt": "",
    "json": "{}"
}



##################################################
# HELPERS
##################################################



def path_from_root(txt: str = "") -> str:
    """
    Return absolute path to the project root directory.
    Can also transform a local path (relative to project root)
    to absolute path (no matter the os (use '/' to sep))
    """
    if not txt: return _ROOT # Return root dir path
    txt.removeprefix("/") # Ensure path may start with '/'
    path = os_path.join(_ROOT, txt.replace('/', os_sep))
    return os_path.normpath(path)


def ensure_file(source: str, value: str, read_only: bool|None, filenotfound: bool|None) -> str|None:
    """
    Ensure the given file (path relative to project root) exists.
    If it does not, filenotfound and read_only define the action to take :
    - True : Create the file and write the value to it (return the absolute path)
    - None (or read_only is True): Ignore (return None)
    - False : Raise FileNotFoundError
    """
    path = path_from_root(source) # Create absolute path from relative
    if not os_path.isfile(path):
        if filenotfound is False: # filenotfound == False -> Raise FileNotFoundError
            raise FileNotFoundError(f"{path} was not found in given directory")
        # If filenotfound set to ignore or there is not write instruction
        elif filenotfound is None or read_only is True: return None
        # Otherwise, make directories, file, and write value
        makedirs(os_path.dirname(path), exist_ok = True)
        with open(path, 'w', encoding="utf-8") as F: F.write(value)
    return path


def explore_struct(struct: dict|list, value = None, *keys: str|int,
        read_only: bool = True, keynotfound: bool|None = None) -> bool:
    """
    Recursively explore the given structure using the keys.
    value : Default value to return / to write

    read_only : Behavior regarding read/write
    - True : Only get from the source, do not set (return the value)
    - None : Write if value doesn't exist (return the value)
    - False : Set/write to source no matter what (return boolean specifying success)

    keynotfound : Action to take if key doesn't exist
    - True : Write in place (create from void)
    - None : Ignore and return early
    - False : Raise KeyError

    str keys expect a dict, int keys are list indicies
    """
    if not keys: raise IndexError("Must provide at least one key arg")
    # First, we evaluate if the structure contains a value for the keys
    if isinstance(struct, dict): present = keys[0] in struct.keys()
    elif isinstance(struct, list): present = keys[0] in range(len(struct))
    else: raise TypeError(f"Cannot explore structure {struct}")

    if not present: # If not available
        # False means we want to raise KeyError
        if keynotfound is False: raise KeyError(f"{keys[0]} was not found in {struct}")
        # None means we ignore and return early
        elif keynotfound is None: return False if read_only is False else value
        # Otherwise, means we continue and create missing entries
        elif len(keys) == 1: # If it's the last key, special case to modify objectby reference
            if read_only is True: return value # Return default if no write
            struct[keys[0]] = value # Otherwise, write the default
            return value if read_only is None else True
        else: # Not the last key ; we create the next structure
            if isinstance(keys[1], str): struct[keys[0]] = {}
            elif isinstance(keys[1], int): struct[keys[0]] = []
            else: raise TypeError(f"Cannot create structure for key {keys[1]}")

    # If keys is 2 or more (so the awaited value is a structure),
    # the key is an int (str keys for dict can be created in place anyway)
    # and the given array is shorter than the upcoming key
    # and keynotfound is True (write the strucure as we go)
    if len(keys) >= 2 and isinstance(keys[1], int) and len(struct[keys[0]]) < keys[1] and keynotfound:
        # Expand the given array to allow for extraction of the request key/index
        # With default value None, or the same as original if exists
        struct[keys[0]] = [struct[keys[0]][i] if i < len(struct[keys[0]]) else None for i in range(keys[1]+1)]
        # Because the value is None, it is not undefined, therefore we need to create it
        # before it reaches the previous part of the code (in charge of initialysing the struct)
        # if another key exists after that (else, we know the expanded struct can have the default value)
        if len(keys) >= 3: struct[keys[0]][keys[1]] = {} if isinstance(keys[2], str) else []
        else: struct[keys[0]][-1] = value
    
    if len(keys) == 1: # If it's the lastkey
        if read_only is False: # If writing
            struct[keys[0]] = value # Set the value
            return True # Return false
        # By this time the default value is already set, so we can ignore read_only == None
        return struct[keys[0]]
    
    # Otherwise, reccursively explore the structure by referencing a lower level
    return explore_struct(struct[keys[0]], value, *keys[1:],
        read_only = read_only, keynotfound = keynotfound)



##################################################
# FUNCTIONS
##################################################



def data(source: str, value = None, *keys, read_only: bool|None = True,
        filenotfound: bool|None = True, keynotfound: bool|None = True) -> bool:
    """
    Import or export data from/to a txt or json file
    source : the path of the file, relative to project root
    value : the default value to read or write

    read_only : Behavior regarding read/write
    - True : Only get from the source, do not set (return the value)
    - None : Write if value doesn't exist (return the value)
    - False : Set/write to source no matter what (return boolean specifying success)

    filenotfound : Action to take if file doesn't exist
    - True : Create the file and write to it
    - None (or read_only is True): Ignore (return None)
    - False : Raise FileNotFoundError

    keynotfound : Action to take if key doesn't exist
    - True : Write in place (create from void)
    - None : Ignore and return early
    - False : Raise KeyError

    Dictionary structure expect str keys, list expect int indicies
    Json file treats the content as a proper OOP structure
    Txt file treats the data as an array (per line) in terms of keys,
    but will always return the requested value as a string
    """
    format = source.split(".")[-1] # Get the file extension
    # If it's nonexistent, not recognized or not handled, raise error
    if format not in _DATA_FORMATS: raise ValueError(f"Cannot get data from source {source}")
    # Ensure the file exist and decide action to take if it doesn't
    path = ensure_file(source, _DATA_FORMATS[format], read_only, filenotfound)
    if path is None: return value if read_only else False
    # Redirect to their respective data functions
    if format == "json": return data_json(path, value, *keys,
        read_only = read_only, keynotfound = keynotfound)
    elif format == "txt": return data_txt(path, value, *keys,
        read_only = read_only, keynotfound = keynotfound)


def data_txt(path: str, value = None, *keys, read_only: bool = True,
        keynotfound: bool|None = True) -> str|bool:
    """
    Data function to read and write from/to .txt files
    See data() for more information on function parameters
    Note that keys[0] (if provided) must be an integer index,
    and keys[1:] will be ingored
    """
    # Open the file and get its content
    with open(path, 'r', encoding="utf-8") as F:
        # Remember that each line finishes by "\n" by default
        content = [l.removesuffix("\n") for l in F.readlines()]

    if not keys: # If the content is the whole file
        # If it's write-only or content is null, content is default value
        if read_only is False or not content: content = "\n".split(value)
        out = "\n".join(content) # Output is just content as a string

    else: # If a key is specified (looking for a line)
        if keys[0] >= len(content): # If doesn't exist
            # False means we want to raise IndexError
            if keynotfound is False: raise IndexError(f"Index {keys[0]} is out of range")
            # None means we ignore and return early
            elif keynotfound is None: return False if read_only is False else value
            # Otherwise, we expand the array to be able to contain the value
            content = [content[i] if i < len(content) else "" for i in range(keys[0]+1)]

        if read_only is True: return value # No writing to do ; return default
        # Writing requested or needed (default value)
        if read_only is False or not content[keys[0]]: content[keys[0]] = value
        out = content[keys[0]] # Output is the specified line

    if read_only is True: return out # No writing ; return output
    # Write to file, each list element separated by a line break
    with open(path, "w", encoding="utf-8") as F: F.write("\n".join(content))
    return out if read_only is None else True


def data_json(path: str, value = None, *keys, read_only: bool = True,
        keynotfound: bool|None = True) -> bool:
    """
    Data function to read and write from/to .json files
    See data() for more information on function parameters
    """
    # Read the file data and parse it from json to a python structure
    with open(path, 'r', encoding="utf-8") as F: content = load(F)
    if not keys: # No keys provided (want the whole object)
        if not content: content = value # Default content is given value
        out = content # Output is content as a whole
    # Otherwise : output is recursive file exploration result
    else: out = explore_struct(content, value, *keys, read_only = read_only, keynotfound = keynotfound)
    if read_only is True: return out # No writing ; return output
    # Write to file as a json-formatted text
    with open(path, "w", encoding="utf-8") as F: dump(content, F, indent=4)
    return out if read_only is None else True



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass
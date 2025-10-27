"""
Action object representing a Twitch API call.
"""



##################################################
# IMPORTS
##################################################



from Modules.data import data



##################################################
# GLOBALS
##################################################



_HELIX_URL = "https://api.twitch.tv/helix/"
ACTIONS = data("Resources/Files/Twitch/actions.json", filenotfound = False)
_TYPES = {"str": str, "int": int, "float": float, "bool": bool, "dict": dict, "list": list}



##################################################
# ACTION
##################################################



class Action:
    """Represent a Twitch Action to be performed via Helix API."""
    def __init__(self, type: str, user: str = None,
                 params: dict = None, json: dict = None, headers: dict = None) -> None:
        if type not in ACTIONS:
            raise ValueError(f"Invalid action type '{type}'"
                f"Expected one of: {list(ACTIONS.keys())}")
        self.type = type
        
        action_data = ACTIONS[type]

        # Check headers, params & json validity (names and types)
        self.headers = check_requirements(
            headers, action_data.get("headers", {})
        ) if headers else None
        self.params = check_requirements(
            params, action_data.get("params", {})
        ) if params else None
        self.json = check_requirements(
            json, action_data.get("json", {})
        ) if json else None

        # TwitchUser instance or Twitch ID string
        self.user = user

        # Build URL and method
        self.url = action_data["url"]
        if not self.url.startswith("http"):
            self.url = _HELIX_URL + self.url
        self.method = action_data.get("method", "GET").upper()



##################################################
# FUNCTIONS
##################################################



def check_requirements(input: dict, template: dict) -> dict:
    """
    Check if the input dictionary matches the template requirements.
    The template can contain types as strings or nested dictionaries.
    """
    filled = {} # Result dictionary

    for k, v in input.items(): # For every entry provided
        if k not in template: # If it is not present in template
            raise ValueError(f"Unknown parameter '{k}'")
        if isinstance(template[k], dict):
            # If nested dict, check recursively
            filled[k] = check_requirements(v, template[k])
        elif isinstance(template[k], str) and template[k] in _TYPES:
            if not isinstance(v, _TYPES[template[k]]): # Type check
                raise TypeError(f"Parameter '{k}' must be of type '{template[k]}', got '{type(v).__name__}'")
        # If static value is present, do not override with template
        filled[k] = v

    for k, v in template.items(): # For every entry in template
        if k in filled: continue # If already filled, skip
        if isinstance(v, dict):
            # If nested dict, fill recursively
            filled[k] = check_requirements({}, v)
        elif v not in _TYPES:
            # Fill default static values
            filled[k] = v
    return filled



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass
"""
Generic discord.py utility functions and method groups.
This is somewhat close to 'basic' MOD, but specifically for discord.py usage.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext.commands import bot as BOT
from discord.ext.commands import Context as CTX



##################################################
# GLOBALS
##################################################



#         typename:   (DSC object class,    get_function,          req_ctx  ),
_TYPES = {"user":     (DSC.User,            "get_user"                      ),
          "member":   (DSC.Member,          "get_member",          "guild"  ),
          "emoji":    (DSC.Emoji,           "get_emoji"                     ),
          "role":     (DSC.Role,            "get_role",            "guild"  ),
          "guild":    (DSC.Guild,           "get_guild"                     ),
          "category": (DSC.CategoryChannel, "get_channel"                   ),
          "channel":  (DSC.TextChannel,     "get_channel"                   ),
          "voice":    (DSC.VoiceChannel,    "get_channel"                   ),
          "message":  (DSC.Message,         "get_partial_message", "channel"),
        }



##################################################
# Converter
##################################################



class DscConverter:
    """Converts discord.py objects."""
    def __init__(self, bot: BOT) -> None:
        self.bot = bot


    @staticmethod
    def id_to_int(input) -> any:
        """
        Transform (input) to a valid object id (does not output which).
        Returns False if input is not an id.
        """
        # If input is already valid, no problem
        if isinstance(input, int):
            if input == 0: raise Exception("wtf") # wtf
            return input
        if isinstance(input, str):
            # Attempt to convert string of numbers to int
            if input.isdigit(): return int(input)
            # Otherwise, check if ID is in <?000> format
            check = any([input.startswith(i) for i in ["<#", "<&@", "<@"]])
            if check and input.endswith(">"):
                input = [i for i in input if i.isdigit()]
                return int("".join(input))
        return False


    @staticmethod
    def gettype(input) -> str:
        """Declare if (input) is either a Discord.Object, an ID, or neither."""
        # If object type is among the list in _TYPES
        for name in _TYPES:
            if isinstance(input, _TYPES[name][0]): return name
        if DscConverter.id_to_int(input):
            return "id"
        else: return ""


    def convertobj(self, input, typename: str, ctx: CTX = None) -> any:
        """
        Transform given input to requested Discord.Object
        """
        # If typename is not known
        if typename not in _TYPES:
            # Attempt to resolve from the current object, as a blessing (or curse) to the future user
            attr = getattr(input, typename, None)
            if attr:
                print(f"Successuffly extracted '{typename}' from a '{type(input).name}'\n" +
                    "If you are seeing this, it probably means a dsc_convertobj() call is unnecessary.")
                return attr
            raise ValueError(f"'{typename}' is not a Discord object class, or not implemented")
        
        # If input is already valid, return it unchanged
        if DscConverter.gettype(input) == typename: return input

        # If it's a valid ID, turn it into an actual int
        id = DscConverter.id_to_int(input)
        if id:
            # If it can be fetched from the BOT
            method = getattr(self.bot, _TYPES[typename][1], None)
            if method: return method(id)
            
            # Otherwise, this means it has to be fetched from CTX
            if len(_TYPES[typename]) != 3: raise TypeError(f"Cannot fetch '{typename}' by ID")
            if not ctx: raise ValueError(f"'{typename}' requires a CTX to be extracted")
            ctx = self.convertobj(self.bot, ctx, _TYPES[typename][2])
            return getattr(ctx, _TYPES[typename][1])(id)

        # Generic test if any scenario above is false
        attr = getattr(input, typename, None)
        if attr: return attr
        raise TypeError(f"Cannot extract '{typename}' from input {input} of type '{type(input).__name__}'")
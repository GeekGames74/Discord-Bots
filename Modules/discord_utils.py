"""
Generic discord.py utility functions and method groups.
This is somewhat close to 'basic' MOD, but specifically for discord.py usage.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext.commands import bot as Bot
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
    def __init__(self, bot: Bot) -> None:
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



##################################################
# FUNCTIONS
##################################################



def find_vc(converter: DscConverter, ctx: CTX, perm1: str = None,
    target: str = None, perm2: str = "") -> DSC.VoiceChannel|bool:
    """
    Find the voiceprotocol to use in the context of a command.
    perms must be a Discord.Permission property or None, with perm1 local|guild and perm2 remote
    """
    if perm1 is not None and (getattr(DSC.Permissions.all(), perm1, None) is None or \
        not isinstance(getattr(DSC.Permissions.all(), perm1), bool)):
            raise ValueError("perm1 is not a Discord.Permission property")
    if perm2 == "": perm2 = perm1
    elif getattr(DSC.Permissions.all(), perm2, None) is None or \
        not isinstance(getattr(DSC.Permissions.all(), perm2), bool):
            raise ValueError("perm2 is not a Discord.Permission property")
    if ctx.guild:
        if target is None:
            if ctx.author.voice: return ctx.author.voice.channel
            if ctx.guild.voice_client and ctx.guild.voice_client.is_connected():
                channel = ctx.guild.voice_client.channel
                if perm1 is None or getattr(channel.permissions_for(ctx.author), perm1): return channel
                return False
            return None
        else: # resolve given channel by guild
            try: channel = converter.convertobj(target, "voice", ctx)
            except TypeError: pass
            if isinstance(channel, DSC.VoiceChannel): 
                if perm1 is None or getattr(channel.permissions_for(ctx.author), perm1):
                    return channel
                return False
            return None
    if target:
        try: guild = converter.convertobj(target, "guild")
        except TypeError: pass
        if isinstance(guild, DSC.Guild):
            member = guild.get_member(ctx.author.id)
            if not member: return None
            if not guild.voice_client: return None
            channel = guild.voice_client.channel
            if not channel: return None
            if perm2 is None or getattr(channel.permissions_for(member), perm2): return channel
            return False
    for guild in ctx.bot.guilds:
        member = guild.get_member(ctx.author.id)
        if not member: continue # only check guilds in common
        if target is None:
            if member.voice:
                if perm2 is None or getattr(member.voice.channel.permissions_for(member), perm2):
                        return member.voice.channel
                return False
        else: # resolve given channel for every guild
            try: target = converter.convertobj(target, "voice", guild)
            except TypeError: pass
            else:
                if isinstance(target, DSC.VoiceChannel): 
                    if perm2 is None or getattr(target.permissions_for(member), perm2):
                        return target
                    return False
                return None
    return None



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass
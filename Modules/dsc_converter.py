"""
Convert and detect discord.py objects.
"""



##########################################################################
# IMPORTS
##########################################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands import Context as CTX



##########################################################################
# GLOBALS
##########################################################################



# (Discord.Object, common_name, get_function) triplets
TYPES = [(CTX, "ctx", None),
         (DSC.Guild, "guild", "get_guild"),
         (DSC.TextChannel, "channel", "get_channel"),
         (DSC.VoiceChannel, "voice", "get_channel"),
         (DSC.Message, "message", "get_partial_message"),
         (DSC.User, "user", "get_user"),
         (DSC.Role, "role", "get_role"),
         (DSC.Member, "member", "get_member"),
         (DSC.CategoryChannel, "category", "get_channel"),
         (DSC.Emoji, "emoji", "get_emoji"),
        ]



##########################################################################
# MAIN FUNCTIONS
##########################################################################



def dsc_toid(input) -> any:
    """Transform (input) to a valid object id (does not output which)."""
    if isinstance(input, int): return input
    if isinstance(input, str):
        if input.isdigit(): return int(input)
        check = any([input.startswith(i) for i in ["<#", "<&@", "<@"]])
        if check and input.endswith(">"):
            input = [i for i in input if i.isdigit()]
            return int("".join(input))
    return False


def dsc_type(input) -> any:
    """Declare if (input) is either a Discord.Object, an ID, or neither."""
    for type_, name, call in TYPES:
        if isinstance(input, type_): return name
    if isinstance(input, int) or isinstance(input, str) and input.isdigit():
        return "id"
    else: return None


def dsc_obj(BOT: CMDS.bot, input, obj: str, ctx = None) -> any:
    """
    Transform given input to requested Discord.Object
    If unable to, raises error.
    """
    if dsc_type(input) == obj: return input
    if dsc_toid(input):
        input = dsc_toid(input)
    if ctx is not None:
        if obj == "message": ctx = dsc_obj(ctx, "channel")
        else: ctx = dsc_obj(ctx, "guild")
    if dsc_type(input) == "id":
        if obj == "guild": return BOT.get_guild(int(input))
        method = getattr(ctx, {name: call for (_, name, call) in TYPES}[obj], None)
        return method(int(input))
    elif dsc_type(input) == "ctx":
        if obj in ["user", "member"]: return input.author
        return getattr(input,obj)
    raise TypeError(f"input {input} of type {type(input)} with request '{obj}' in dsc_obj()")
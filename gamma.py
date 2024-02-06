"""
Gamma Discord Bot
By GeekGames74 (@geek74)
"""

__author__ = "GeekGames74"
__email__ = "geekgames74.fr@gmail.com"
__version__ = "2.0.0"


print("Started")



##########################################################################
# REQUIREMENTS AND IMPORTS
##########################################################################



import os

import discord as DSC
from discord import *
from discord.ext import commands as CMDS
from discord.ext.commands import Context as CTX

import asyncio
from nest_asyncio import apply as asyncio_apply

from traceback import print_exception

from math import factorial, pi
from dice import roll as ROLL



##########################################################################
# DATA AND CREDENTIALS
##########################################################################



def del_env(var) -> None:
    """Delete (var) from execution environment, or at least obfuscate it."""
    if isinstance(var, str):
        globals()[var] = "HIDDEN"
        exec(f"{var} = 'HIDDEN'")
        exec(f"del {var}")
    # (var) can also be a list of variables to del_env()
    elif isinstance(var, list):
        for i in var:
            del_env(i)


def del_i() -> None:
    """Remove code from the environment, as a precaution."""
    del_env("In")
    i = 0
    while i < len(globals()):
        if list(globals().keys())[i].startswith("_i"):
            del_env(list(globals().keys())[i])
        else: i += 1


def local_path() -> str:
    return os.path.dirname(os.path.realpath(__file__))


def check_file(name: str) -> str:
    """Tries to resolve given path."""
    path = local_path() + name
    name.replace("/", os.sep)
    if os.path.isfile(f"{path}"):
        return f"{path}"
    raise FileNotFoundError(f"{path} was not found in current directory")


def with_data(where: str, data: any):
    """
    TXT: Obtain requested data with {VarName: identifier}
    """
    def decorator(func: callable) -> callable:
        def wrapper(*args, **kwargs) -> any:
            if where.endswith(".txt"):
                local_data = data_TXT(where, data)
            else: raise NotImplementedError(f"Cannot get data from {where}")
            kwargs.update(local_data)
            result = func(*args, **kwargs)
            del_env(["data", "local_dta"])
            return result
        return wrapper
    return decorator


# Data from .txt
def data_TXT(file: str, data: dict) -> dict:
    file = check_file(file)
    local_data = {}
    with open(file) as F:
        lines = F.readlines()
    # Remember : readline() might return "\n" at the end of the line
    for i,j in data.items():
        local_data[i] = lines[j].removesuffix("\n")
    del_env(["file", "data", "lines"])
    return local_data



##########################################################################
# BOT SETUP
##########################################################################



# Intents required by the bot. Limit to minimum.
intents = DSC.Intents.default()
intents.message_content = True
intents.members = True


PREFIX = "/"
BOT = CMDS.Bot(command_prefix = PREFIX,
               intents = intents,
               case_insensitive = True,
               strip_after_prefix = True,
               activity = DSC.Activity(),
              )



##########################################################################
# GLOBALS AND METHODS
##########################################################################



VIP = {}
async def GetVIPs() -> None:
    VIP["Geek"] = BOT.get_user(427031555383492609)
    VIP["Ghost"] = BOT.get_user(774648396719194112)
    VIP["Yollow"] = BOT.get_user(466607185145626634)
    VIP["Volk"] = BOT.get_user(441684181932703744)
    VIP["Huli"] = BOT.get_user(481347795396329482)
    VIP["Galina"] = BOT.get_user(993173798515916902)


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


def dsc_obj(input, obj: str, ctx = None) -> any:
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



##########################################################################
# UTILITY
##########################################################################



def least_one(text, checkfor) -> bool:
    """Check if there is at least one of (checkfor) in (text)."""
    return any(i in text for i in checkfor)


# Dynamic reaction general-use function to interract
# neatly with user. Several parameters available.
# Command uses exec() -> Be careful with usage.
# Consider subfunctions for regularly-used cases.
async def reactech(ctx, emoji: str, react: bool = True,
                   recursive: int = -1, timeout: int = 3600, cond: str = "True",
                   method: str = "pass", *args) -> None:
    msg = dsc_obj(ctx, "message")
    if react: await msg.add_reaction(emoji)
    # Here the Bot waits for a reaction add that matches (check)
    def check(reaction: DSC.Reaction, user: DSC.User) -> bool:
        return (msg == reaction.message
                and emoji == reaction.emoji and user != BOT.user
                and eval(cond, globals(), locals()|{"ctx": ctx, "emoji": emoji}))
    # (reaction) and (user) are kept fo method purposes
    try:
      reaction, user = await BOT.wait_for("reaction_add",
                                           check = check, timeout = timeout)
    except asyncio.TimeoutError: pass
    except Exception as e: raise e
    # If an user reacts, it executes the method
    else:
        try: await eval(method, globals(), locals())
        except Exception as e: raise e
        else:
            # Able to repeat this process until Bot disconnect
            if recursive != 0:
                await reactech(msg, emoji, False, recursive-1,
                               timeout, cond, method, *args)


# REACTECH SUBFUNCTIONS
# rt_er : send error : to user, recursive
# rt_ok : confirm message : send once in channel, then to users

async def rt_er(ctx, emoji: str, txt: str) -> None:
    await reactech(ctx, emoji, True, -1, 300, "True", "user.send(*args)", txt)

async def rt_ok(ctx, txt: str) -> None:
    await reactech(ctx, "✅", True, -1, 3600, "True", "rt_ok_(msg,user,recursive,args)", txt)
async def rt_ok_(msg: DSC.Message, user: DSC.User, recursive: int, txt: str) -> None:
    if recursive == -1:
        await msg.channel.send(*txt)
    else:
        await user.send(*txt)



##########################################################################
# EVAL & ROLL
##########################################################################



def greater_than(left, right) -> int:
    return 1 if left > right else 0
def lesser_than(left, right) -> int:
    return 1 if left < right else 0
def greater_eq_than(left, right) -> int:
    return 1 if left >= right else 0
def lesser_eq_than(left, right) -> int:
    return 1 if left <= right else 0


def main_math(msg, auto: bool = False) -> (any,str):
    """
    Automatically detect and evaluate math and rolling expression from msg.
    <auto> makes it require more checks, used to filter msg_math().
    """
    if msg == "pi" : return (pi, "math")
    msg = msg.replace("pi", "p")
    isdice = True if "d" in msg else False
    allow = "0123456789()+-*/!.,^<=>p"
    if isdice: allow += "%dtsefxahmovl@"
    txt = "".join([i for i in msg if i in allow])
    
    _ = ("","error")
    if auto:
        if len(msg) > 50: return _
        if len(txt) < 2 or (len(txt) < 3 and not isdice): return _
        if len(txt) < 0.5*len(msg): return _
        if not least_one(txt, "0123456789p"): return _
        if not isdice and not least_one(txt, "+-*/!^<>"): return _
        if least_one(msg, ["<#","<@","<@&", "\n"]): return _
   
            
    if isdice:
        if "@" in txt:
            if txt.count("@") > 2:
                return ("Attack", "error")
            attack = txt.split("@")
            if txt.count("@") == 1: attack.append("1")
            try: return (greater_eq_than(main_math(attack[0])[0],
                                         main_math(attack[1])[0])*
                                         main_math(attack[2])[0],
                                         "attack")
            except Exception as e: return (e,"error")
        
        elif least_one(txt, ["**", ">=", "<="]) or least_one(txt, "!><p"):
            return ("Mix", "error")
    
    else:
        txt = txt.replace("^", "**")
        txt = txt.replace("!", "factorial")
        txt = txt.replace(">=", "greater_eq_than")
        txt = txt.replace("<=", "lesser_eq_than")
        txt = txt.replace(">", "greater_than")
        txt = txt.replace("<", "lesser_than")
        txt = txt.replace("p", "pi")

    try:
        if not isdice:
            result = eval(txt)
        else:
            result = ROLL(txt)
    except Exception as e:
        return (e,"error")
    
    type_ = "dice" if isdice else "math"
    if isinstance(result, list): result = sum(result)
    if auto and str(result) == txt: return _
    return (result,type_)


@BOT.command(name = "calculate", aliases = ["calc", "c", "math",
                                       "eval", "evaluate",
                                       "roll", "dice", "r", "d"])
async def calculate(ctx: CTX, *, txt: str) -> any:
    """
    Allows mathematical evaluation of a simple expression (it's a calculator !)
    Can also dice.py notations (see https://pypi.org/project/dice/).
    Can also use factorial '!(5)', pi 'p', and comparisons '<=(5,10)'.
    Using '@' permits dice notation within a 'greater than or equal to', such as:
    '1d20@15@2d6' means '>=(1d20,15)*2d6'
    """
    result = main_math(txt)
    if result[1] == "error":
        awaiter = [rt_er(ctx, "⁉️", result[0])]
        if "d" in txt:
            awaiter += [rt_er(ctx, "🆘", "Dice notation: https://pypi.org/project/dice/")]
        if result[0] == "Mix":
            await rt_er(ctx, "🚫", "Cannot use complex math (factorial, power, comparison) and dice at the same time!")
        elif result[0] == "Attack":
            await rt_er(ctx, "🚫", "Cannot use more than 2 Attack markers")
        else:
            asyncio.gather(*awaiter)
    else:
        await ctx.send(result[0])


# Only notifies of available answer if it produces no error
async def msg_math(msg: DSC.message) -> None:
    result = main_math(msg.content, True)
    if result[1] != "error":
        emote = {"math":"🧮", "dice":"🎲", "attack":"⚔️"}[result[1]]
        await reactech(msg, emote, True, 0, 3600, "True", f"msg.channel.send('{result[0]}')")



##########################################################################
# SYSTEM
##########################################################################



@BOT.command(name = "ping", aliases = ["test", "!", "latency"])
async def ping(ctx: CTX = None) -> int:
    if ctx is not None:
        await ctx.send("pong! " + str(int(BOT.latency*1000)) + "ms")
    return BOT.latency


# Evaluates expression or runs code from Discord
# Uses exec() : Be careful of input !
@BOT.command(name = "echo", aliases = ['console', 'send', 'exec', 'command',' cmd', 'execute'])
@CMDS.is_owner()
async def echo(ctx: CTX, *, txt: str) -> None:
    print(txt)
    try: await eval(txt)
    except SyntaxError:
        try: exec(txt)
        except Exception as e: raise e
    except Exception as e: print(e)


@BOT.command(name = "activity", aliases = ["status"])
@CMDS.is_owner()
async def activity(ctx: CTX, action: str = "", *, txt = None) -> DSC.Activity:
    """
    Changes current bot activity and status message
    Activity is designated with keywords in (action)
    """
    action = action.lower()
    if 'twitch.tv/' in action: url = action.removeprefix("https://").removeprefix("www.")
    else : url = "twitch.tv/"
    url = "https://" + url
    activity = None
    if least_one(action, ['gam', 'play']) : activity = DSC.Game(name = txt)
    if least_one(action, ['stream', 'twitch']) : activity = DSC.Streaming(name = txt, url = url)
    if least_one(action, ['listen']) : activity = DSC.Activity(type = DSC.ActivityType.listening, name = txt)
    if least_one(action, ['watch', 'video']) : activity = DSC.Activity(type = DSC.ActivityType.watching, name = txt)
    if least_one(action, ['def', 'serv', 'bas', 'main']) : activity = "Default"
    if activity is None:
        activity = "Set activity to None"
        await BOT.change_presence(activity = None)
    else:
        if txt is None or activity == "Default":
            txt = str(len(BOT.guilds)) + ' servers'
            activity = DSC.Activity(type = DSC.ActivityType.watching, name = txt)
        await BOT.change_presence(activity = activity)
    if ctx: await rt_ok(ctx, activity)
    return activity


@BOT.command(name = "kill", aliases = ["killtask", "end", "endtask", "destroy", "shutdown", "exit"])
@CMDS.is_owner()
async def kill(ctx: CTX = None) -> None:
    if ctx: await ctx.message.add_reaction("✅")
    await END()



##########################################################################
# LOOPS AND EVENTS
##########################################################################



@BOT.event
async def on_message(msg: DSC.message) -> None:
    await BOT.process_commands(msg)
    if msg.content.startswith(PREFIX): return
    if msg.author == BOT.user: return
    await msg_math(msg)



##########################################################################
# ERRORS
##########################################################################



@BOT.event
async def on_command_error(ctx: CTX, error):
    # Message to display on error, along with react emoji
    a= ("⛔","This command requires a role or permission you do not posess.\nIf you think this is a mistake, contact server admins.")
    b= ("📛","This command can only be operated by a bot admin.\nIf you think this is a mistake, contact the developer(s).")
    c= ("🚫","This command cannot be utilized in the current context.\nRefer to the Error name for more precision.")
    d= ("⁉️","This command was wrongfully formatted or does not exist.\nConsult proper usage using the HELP command.")
    e= ("❓","A required Discord Object could not be resolved.\nMake sure your object names or IDs are correct before trying again.")
    f= ("‼️","The bot could not execute this command.\nMake sure to setup the application properly.")
    # Link every (most) errors with its proper message
    errors=[
        (CMDS.MissingPermissions,a),
        (CMDS.NotOwner,b),
        (CMDS.MissingRole,a),
        (CMDS.MissingAnyRole,a),
        (CMDS.DisabledCommand,c),
        (CMDS.CommandOnCooldown,c),
        (CMDS.NSFWChannelRequired,c),
        (CMDS.MissingRequiredArgument,d),
        (CMDS.TooManyArguments,d),
        (CMDS.BadArgument,d),
        (CMDS.UnexpectedQuoteError,d),
        (CMDS.CommandNotFound,d),
        (CMDS.MessageNotFound,e),
        (CMDS.MemberNotFound,e),
        (CMDS.UserNotFound,e),
        (CMDS.ThreadNotFound,e),
        (CMDS.ChannelNotFound,e),
        (CMDS.RoleNotFound,e),
        (CMDS.GuildNotFound,e),
        (CMDS.EmojiNotFound,e),
        (CMDS.GuildStickerNotFound,e),
        (CMDS.ScheduledEventNotFound,e),
        (CMDS.BotMissingPermissions,f),
        (CMDS.BotMissingRole,f),
        (CMDS.BotMissingAnyRole,f),
        (CMDS.ChannelNotReadable,f)]
    for type_, i in errors:
        if isinstance(error, type_):
            print(type_,i)
            await rt_er(ctx, i[0], i[1])
            return
    print_exception(type(error), error, error.__traceback__)



##########################################################################
# RUN
##########################################################################



@BOT.event
async def on_connect():
    print("\nConnecting\n")
    del_env("TOKEN")
    del_i()


@BOT.event
async def on_ready():
    print("\nConnected\n\n")
    await activity(None, "Default")
    await GetVIPs()


@BOT.event
async def on_disconnect():
    print("\nDisconnected")


@with_data("/Credentials/GAMMA_TOKEN.txt", {"TOKEN": 0})
def RUN(TOKEN):
    asyncio_apply()
    BOT.run(TOKEN, reconnect = True)


async def END():
    print("\nDisconnecting\n")
    await BOT.close()


RUN()

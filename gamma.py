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
import sys

import discord as DSC
from discord import *
from discord.ext import commands as CMDS
from discord.ext.commands import Context as CTX

import asyncio
from nest_asyncio import apply as asyncio_apply

from traceback import print_exception

from math import factorial, pi
from dice import roll as ROLL

sys.path.append(os.path.join(local_path(__file__), 'Modules'))
from Modules.basic import *
from Modules.reactech import *



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


def check_file(name: str) -> str:
    """Tries to resolve given path."""
    path = local_path(__file__) + name
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
        awaiter = [rt_err(BOT, ctx, "⁉️", result[0])]
        if "d" in txt:
            awaiter += [rt_err(BOT, ctx, "🆘", "Dice notation: https://pypi.org/project/dice/")]
        if result[0] == "Mix":
            await rt_err(BOT, ctx, "🚫", "Cannot use complex math (factorial, power, comparison) and dice at the same time!")
        elif result[0] == "Attack":
            await rt_err(BOT, ctx, "🚫", "Cannot use more than 2 Attack markers")
        else:
            asyncio.gather(*awaiter)
    else:
        await ctx.send(result[0])


# Only notifies of available answer if it produces no error
async def msg_math(msg: DSC.message) -> None:
    result = main_math(msg.content, True)
    if result[1] != "error":
        emote = {"math":"🧮", "dice":"🎲", "attack":"⚔️"}[result[1]]
        await reactech(BOT, msg, emote, True, 0, 3600, "True", f"msg.channel.send('{result[0]}')")



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
    if ctx: await rt_ok(BOT, ctx, activity)
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
            await rt_err(BOT, ctx, i[0], i[1])
            return
    print_exception(type(error), error, error.__traceback__)



##########################################################################
# RUN
##########################################################################



@BOT.event
async def on_connect():
    print("\nConnecting\n")
    del_i()


@BOT.event
async def on_ready():
    print("\nConnected\n\n")
    # <LOAD HERE>
    await GetVIPs()
    await activity(None, "Default")


@BOT.event
async def on_disconnect():
    print("\nDisconnected")


@with_data("/Credentials/GAMMA_TOKEN.txt", {"TOKEN": 0})
def RUN(TOKEN):
    asyncio_apply()
    BOT.run(TOKEN, reconnect = True)


async def END():
    # <SAVE HERE>
    print("\nDisconnecting\n")
    await BOT.close()


RUN()

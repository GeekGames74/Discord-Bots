"""
Gamma Discord Bot
By GeekGames74 (@geek74)
"""

__author__ = "GeekGames74"
__email__ = "geekgames74.fr@gmail.com"
__version__ = "2.0.0"



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands import Context as CTX

from asyncio import gather
from nest_asyncio import apply

from math import factorial, pi
from dice import roll as ROLL

from Modules.basic import *
from Modules.reactech import Reactech
from Modules.data import with_data
from Modules.botbuilder import build_bot



##################################################
# BOT
##################################################



PREFIX = "/"
BOT = build_bot("gamma.json")
REACTECH = Reactech(BOT)



##################################################
# GLOBALS
##################################################



VIP = {}
async def GetVIPs() -> None:
    VIP["Geek"] = BOT.get_user(427031555383492609)
    VIP["Ghost"] = BOT.get_user(774648396719194112)
    VIP["Yollow"] = BOT.get_user(466607185145626634)
    VIP["Volk"] = BOT.get_user(441684181932703744)
    VIP["Huli"] = BOT.get_user(481347795396329482)
    VIP["Galina"] = BOT.get_user(993173798515916902)



##################################################
# EVAL AND ROLL
##################################################



def main_math(msg: str, auto: bool = False) -> (any,str):
    """
    Automatically detect and evaluate math and rolling expression from msg.
    <auto> makes it require more checks, used to filter msg_math().
    """
    msg = msg.lower()
    # If the user literally asks for pi
    if msg == "pi" : return (pi, "math")
    # Turn pi into p (after 'pi' check, we do not accept 'p')
    msg = msg.replace("pi", "p")
    # Does the request use dice notation ?
    isdice = True if "d" in msg else False
    # Default allowed characters list
    allow = "0123456789()+-*/!.,^<=>p"
    # Extended allowed characters list
    if isdice: allow += "%dtsefxahmovl"
    # Filter the message
    txt = "".join([i for i in msg if i in allow])
    
    _ = ("", "error") # Default error return
    if auto:
        if len(msg) > 50: return _ # Max 50 characters
        # At least 3 characters (1+1), or 2 if dice (d4)
        if len(txt) < 2 or (len(txt) < 3 and not isdice): return _
        # Less than 25% of the message is allowed (not counting spaces)
        if len(txt) < 0.75*len(msg.replace(" ", "")): return _
        # At least one number (or pi)
        if not least_one(txt, "0123456789p"): return _
        # Either dice or math (don't tell the user 123 = 123)
        if not isdice and not least_one(txt, "+-*/!^<>"): return _
        # Just in case, no IDs and not newlines
        if least_one(msg, ["<#","<@","<@&", "\n"]): return _
   
    # Cannot use both dice and complex math (technical limitation)
    if isdice and (least_one(txt, ["**", ">=", "<="]) or least_one(txt, "!><p")):
        return ("Mix", "error")
    
    if not isdice: # Define helper functions, then replace text
        def greater_than(left, right) -> int:
            return 1 if left > right else 0
        def lesser_than(left, right) -> int:
            return 1 if left < right else 0
        def greater_eq_than(left, right) -> int:
            return 1 if left >= right else 0
        def lesser_eq_than(left, right) -> int:
            return 1 if left <= right else 0

        txt = txt.replace("^", "**")
        txt = txt.replace("!", "factorial")
        txt = txt.replace(">=", "greater_eq_than")
        txt = txt.replace("<=", "lesser_eq_than")
        txt = txt.replace(">", "greater_than")
        txt = txt.replace("<", "lesser_than")
        txt = txt.replace("p", "pi")

    try: # Calculation
        if not isdice: # Complex (or default) math
            result = eval(txt)
        else: # Dice usage
            result = ROLL(txt)
    except Exception as e:
        return (e, "error")
    
    type_ = "dice" if isdice else "math"
    # (3d20) returns [1d20, 1d20, 1d20]. Most commonly, users want the sum
    if isinstance(result, list): result = sum(result)
    # If literally nothing has changed anyway (and we are in auto), forget it
    if auto and str(result) == txt: return _
    return (result, type_)


@BOT.command(name = "calculator", aliases = ["calculate", "calc", "evaluate", "eval", "math",
                                            "dice", "roll", "d", "r", "diceroll", "rolldice"])
async def calculate(ctx: CTX, *, txt: str) -> None:
    """
    Allows mathematical evaluation of a simple expression (it's a calculator !)
    Can also dice.py notations (see https://pypi.org/project/dice/).
    Can also use factorial '!(5)', pi 'p', and comparisons '<=(5,10)'.
    """
    result = main_math(txt)
    if result[1] == "error":
        if result[0] == "Mix":
            await REACTECH.reactech_error(ctx, "🚫",
            "Cannot use complex math (factorial, power, comparison) and dice at the same time!"); return
        # If the error is not a mix, then simply log it to the user
        awaiter = [REACTECH.reactech_error(ctx, "⁉️", result[0])]
        if "d" in txt: # Include dice documentation if relevant
            awaiter += [REACTECH.reactech_error(ctx, "🆘", "Dice notation: https://pypi.org/project/dice/")]
        gather(*awaiter) # Send error(s) as reactions
    else: await ctx.send(result[0]) # Send result


async def msg_math(msg: DSC.message) -> None:
    result = main_math(msg.content, True)
    if result[1] != "error": # Only send if it's not an error
        emote = {"math":"🧮", "dice":"🎲"}[result[1]]
        await REACTECH.reactech(msg, emote, True, 0, 3600, None, f"msg.channel.send('{result[0]}')")



##################################################
# SYSTEM
##################################################



@BOT.command(name = "ping", aliases = ["test", "!", "latency"])
async def ping(ctx: CTX) -> None:
    """Returns the current latency between discord and the bot."""
    await ctx.send("pong! " + str(int(BOT.latency*1000)) + "ms")


# Evaluates expression or runs code from Discord
# Uses exec() : Be careful of input !
@BOT.command(name = "echo", aliases = ['console', 'send', 'exec', 'command',' cmd', 'execute'])
@CMDS.is_owner()
async def echo(ctx: CTX, *, txt: str) -> None:
    """
    Executes a command or evaluates an expression.
    Usage is reserved for bot developpers / admins, for testing purposes.
    Report any and every case of abuse to the bot support.
    """
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
    Changes current bot activity and status message.
    Activity is designated with generic keywords.
    """
    action = action.lower()
    url = "twitch.tv/" # Default url
    # Does not work with www.
    if 'twitch.tv/' in action:
        url = action.replace("www.", "")
    # Does not work without https://
    if not url.startswith("https://"): 
        url = "https://" + url

    activity = None
    if least_one(action, ['gam', 'play']):
        activity = DSC.Game(name = txt)
    if least_one(action, ['stream', 'twitch']):
        activity = DSC.Streaming(name = txt, url = url)
    if least_one(action, ['listen']):
        activity = DSC.Activity(type = DSC.ActivityType.listening, name = txt)
    if least_one(action, ['watch', 'video']):
        activity = DSC.Activity(type = DSC.ActivityType.watching, name = txt)
    if least_one(action, ['def', 'serv', 'bas', 'main']):
        activity = "Default"
    
    if activity is None: # Void
        activity = "Set activity to None"
        await BOT.change_presence(activity = None)
    else: # Anything but the void
        if txt is None or activity == "Default":
            txt = str(len(BOT.guilds)) + " servers" # Default message
            activity = DSC.Activity(type = DSC.ActivityType.watching, name = txt)
        await BOT.change_presence(activity = activity)
    if ctx: await REACTECH.reactech_valid(ctx, activity) # Feedback
    return activity


@BOT.command(name = "kill", aliases = mixmatch(["kill", "end", "destroy", "exit", "stop", "terminate"],
            ["", "bot", "task", "script", "instance", "yourself"], keeporder = True, remove = "kill"))
@CMDS.is_owner()              # /kill-yourself is now a valid command (yipee ..?)
async def kill(ctx: CTX) -> None:
    """Save and quit the bot instance."""
    await ctx.message.add_reaction("✅") # Feedback
    await END()



##################################################
# EVENTS
##################################################



@BOT.event
async def on_message(msg: DSC.message) -> None:
    await BOT.process_commands(msg)
    if msg.content.startswith(BOT.command_prefix): return # If it's not a bot command
    if msg.author == BOT.user: return # And not sent by itself
    await msg_math(msg)



##################################################
# ERRORS
##################################################



@BOT.event
async def on_command_error(ctx: CTX, error):
    # Message to display on error, along with react emoji
    a= ("⛔","This command requires a role or permission you do not posess.\nIf you think this is a mistake, contact server admins.")
    b= ("📛","This command can only be operated by a bot admin.\nIf you think this is a mistake, contact the developer(s).")
    c= ("🚫","This command cannot be utilized in the current context.\nRefer to the error name for more precision.")
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
            print(type_, i)
            await REACTECH.reactech_error(ctx, i[0], i[1])
            return
    print(error) # 'print()' or 'raise' depending on your needs



##################################################
# RUN
##################################################



@BOT.event
async def on_connect():
    print("\nCONNECTING\n")


@BOT.event
async def on_ready():
    print("\nCONNECTED\n\nLOADING\n")
    # <LOAD BELLOW>
    await GetVIPs()
    await activity(None, "Default")
    # <LOAD ABOVE>
    print("\nLOADED\n")


async def END():
    print("\nSAVING\n")
    # <SAVE BELLOW>
    # <SAVE ABOVE>
    print("\nSAVED\n\nDISCONNECTING\n")
    await BOT.close()


@BOT.event
async def on_disconnect():
    # No code here (no garantee to be executed)
    print("\nDISCONNECTED\n")


@with_data("/Credentials/GAMMA_TOKEN.txt", {"TOKEN": 0})
def RUN(TOKEN):
    apply()
    BOT.run(TOKEN, reconnect = True)


if __name__ == "__main__":
    print("\nSTARTING\n")
    RUN()
